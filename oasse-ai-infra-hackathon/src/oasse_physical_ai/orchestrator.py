"""Governed dispatch with explicit failure and execution-outcome reporting."""
from __future__ import annotations

from dataclasses import replace
import os
import threading
import time
from typing import Optional

from .dispatch import DispatchGuard, fingerprint, validate_inputs
from .gatekeeper_client import AuthorityClient, build_authority_client
from .metrics import Metrics
from .models import AuthorityDecision, DispatchResult, EvidenceFrame, ProposedAction, Verdict, physically_changed
from .normalization import plain
from .receipts import ReceiptChain
from .providers.actuator import Actuator, SimulatedActuator
from .providers.perception import MockPerceptionProvider, PerceptionProvider
from .providers.vla import MockVLAProvider, VLAProvider


def executable(decision: AuthorityDecision) -> bool:
    if decision.verdict not in {Verdict.ALLOW, Verdict.TRANSFORM} or decision.authorized_action is None:
        return False
    action = decision.authorized_action
    if any(getattr(action, key) != getattr(decision.original_action, key)
           for key in ("action_id", "actor_id", "evidence_id")):
        return False
    if decision.verdict == Verdict.ALLOW:
        return action == decision.original_action
    return physically_changed(action, decision.original_action)


class PhysicalAIOrchestrator:
    def __init__(self, authority: Optional[AuthorityClient] = None,
                 perception: Optional[PerceptionProvider] = None,
                 vla: Optional[VLAProvider] = None, actuator: Optional[Actuator] = None,
                 dispatch_guard: Optional[DispatchGuard] = None) -> None:
        self.authority = build_authority_client() if authority is None else authority
        self.perception = MockPerceptionProvider() if perception is None else perception
        self.vla = MockVLAProvider() if vla is None else vla
        self.actuator = SimulatedActuator() if actuator is None else actuator
        ttl = getattr(self.authority, "evidence_max_age_ms", int(os.getenv("EVIDENCE_MAX_AGE_MS", "500")))
        self.dispatch_guard = DispatchGuard(ttl) if dispatch_guard is None else dispatch_guard
        self.receipts = ReceiptChain()
        self.metrics = Metrics()
        self._lock = threading.RLock()

    def run(self, scenario: str = "allow") -> DispatchResult:
        with self._lock:
            return self._run(scenario)

    def _failure(self, reason: str, start: int) -> DispatchResult:
        # Do not seal arbitrary invalid/cyclic objects or invent a valid observation.
        evidence = EvidenceFrame.fresh(confidence=0.0, workspace_clear=False,
                                       metadata={"provider": "pipeline-error", "observation_available": False})
        action = ProposedAction.pick_place(evidence.evidence_id, action_type="invalid", speed_mps=0.0, trajectory=[])
        decision = AuthorityDecision("failure-" + action.action_id, Verdict.HOLD, [reason], action,
                                     None, evidence, int(time.time() * 1000), 0.0, "pipeline-local-failure-v1")
        receipt = self.receipts.seal("AUTHORITY_DECISION", decision.to_dict())
        elapsed = (time.perf_counter_ns() - start) / 1e6
        self.metrics.record("HOLD", 0.0, elapsed)
        return DispatchResult(decision, receipt, False,
                              {"status": "NOT_EXECUTED", "reason": reason}, None, elapsed, False)

    @staticmethod
    def _held(decision: AuthorityDecision, reason: str) -> AuthorityDecision:
        return replace(decision, verdict=Verdict.HOLD, authorized_action=None,
                       reason_codes=[*decision.reason_codes, reason])

    def _run(self, scenario: str) -> DispatchResult:
        start = time.perf_counter_ns()
        try:
            evidence = self.perception.observe(scenario)
            validate_inputs(evidence)
            evidence_hash = fingerprint(evidence)
        except Exception:
            return self._failure("PERCEPTION_INVALID", start)
        try:
            action = self.vla.propose(evidence, scenario)
            validate_inputs(evidence, action)
            if fingerprint(evidence) != evidence_hash:
                return self._failure("EVIDENCE_CHANGED_BY_PLANNER", start)
            action_hash = fingerprint(action)
        except Exception:
            return self._failure("PROPOSAL_INVALID", start)
        try:
            decision = self.authority.evaluate(evidence, action)
            if not isinstance(decision, AuthorityDecision):
                return self._failure("AUTHORITY_DECISION_INVALID", start)
            if fingerprint(decision.evidence) != evidence_hash or fingerprint(decision.original_action) != action_hash:
                return self._failure("AUTHORITY_BINDING_CHANGED", start)
            if fingerprint(evidence) != evidence_hash or fingerprint(action) != action_hash:
                return self._failure("AUTHORITY_INPUT_MUTATED", start)
            if decision.authorized_action is not None:
                validate_inputs(evidence, decision.authorized_action)
            if action.evidence_id != evidence.evidence_id and decision.verdict in {Verdict.ALLOW, Verdict.TRANSFORM}:
                decision = self._held(decision, "EVIDENCE_BINDING_MISMATCH")
            dispatchable = executable(decision)
            if dispatchable:
                reason = self.dispatch_guard.check(evidence, action)
                if reason:
                    decision = self._held(decision, reason)
                    dispatchable = False
            decision_receipt = self.receipts.seal("AUTHORITY_DECISION", decision.to_dict())
        except Exception:
            return self._failure("AUTHORITY_DECISION_INVALID", start)

        outcome_receipt = None
        attempted = False
        executed = False
        actuator_result = {"status": "NOT_EXECUTED", "reason": decision.verdict.value}
        if dispatchable:
            # Receipt construction and upstream calls may have consumed the TTL.
            try:
                reason = self.dispatch_guard.check(evidence, action)
            except Exception:
                reason = "DISPATCH_CHECK_FAILED"
            if reason:
                decision = self._held(decision, reason)
                decision_receipt = self.receipts.seal("AUTHORITY_DECISION", decision.to_dict())
                actuator_result = {"status": "NOT_EXECUTED", "reason": reason}
            else:
                self.dispatch_guard.consume(evidence, action)
                attempted = True
                try:
                    guarded = getattr(self.actuator, "execute_guarded", None)
                    if callable(guarded):
                        result = guarded(decision.authorized_action, lambda: self.dispatch_guard.freshness(evidence))
                    else:
                        result = self.actuator.execute(decision.authorized_action)
                    actuator_result = plain(result)
                    if not isinstance(actuator_result, dict):
                        raise TypeError("actuator result is not an object")
                    status = actuator_result.get("status", "UNKNOWN")
                    if status not in {"EXECUTED", "NOT_EXECUTED", "FAILED", "UNKNOWN"}:
                        status = "UNKNOWN"
                    actuator_result["status"] = status
                    executed = status == "EXECUTED"
                except Exception as exc:
                    actuator_result = {"status": "UNKNOWN", "reason": "ACTUATOR_ERROR", "error_type": type(exc).__name__}
                outcome_receipt = self.receipts.seal("PHYSICAL_OUTCOME", {
                    "decision_receipt_hash": decision_receipt.receipt_hash,
                    "decision_id": decision.decision_id,
                    "authorized_action_id": decision.authorized_action.action_id,
                    "dispatch_attempted": True, "execution_confirmed": executed,
                    "actuator_result": actuator_result,
                })
        elif decision.verdict == Verdict.TRANSFORM:
            reason = "TRANSFORM_WITHOUT_AUTHORIZED_ACTION" if decision.authorized_action is None else "TRANSFORM_WITHOUT_AUTHORIZED_CHANGE"
            actuator_result = {"status": "NOT_EXECUTED", "reason": reason}
        elapsed = (time.perf_counter_ns() - start) / 1e6
        self.metrics.record(decision.verdict.value, decision.authority_latency_ms, elapsed)
        return DispatchResult(decision, decision_receipt, executed, actuator_result, outcome_receipt, elapsed, attempted)
