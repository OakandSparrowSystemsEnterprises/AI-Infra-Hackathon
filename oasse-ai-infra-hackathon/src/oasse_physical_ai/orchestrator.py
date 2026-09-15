"""Governed observation, evaluation and dispatch with isolated data snapshots."""
from __future__ import annotations

from dataclasses import replace
import os
import threading
import time
from typing import Optional

from .dispatch import DispatchGuard, validate_inputs, copy_action, copy_evidence, copy_decision
from .gatekeeper_client import AuthorityClient, build_authority_client
from .metrics import Metrics
from .models import AuthorityDecision, DispatchResult, EvidenceFrame, ProposedAction, Verdict, physically_changed
from .normalization import plain
from .receipts import ReceiptChain
from .tenki import PreAuthorityEvidenceProvider, TenkiEvidenceError, build_tenki_provider
from .providers.actuator import Actuator, SimulatedActuator
from .providers.perception import MockPerceptionProvider, PerceptionProvider
from .providers.vla import MockVLAProvider, VLAProvider


class ReceiptIntegrityError(RuntimeError):
    """No new effect may run against a previously corrupted receipt chain."""


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
                 dispatch_guard: Optional[DispatchGuard] = None,
                 pre_authority: Optional[PreAuthorityEvidenceProvider] = None) -> None:
        self.authority = build_authority_client() if authority is None else authority
        self.perception = MockPerceptionProvider() if perception is None else perception
        self.vla = MockVLAProvider() if vla is None else vla
        self.actuator = SimulatedActuator() if actuator is None else actuator
        self.pre_authority = build_tenki_provider() if pre_authority is None else pre_authority
        ttl = getattr(self.authority, "evidence_max_age_ms", None)
        if ttl is None:
            ttl = int(os.getenv("EVIDENCE_MAX_AGE_MS", "500"))
        self.dispatch_guard = DispatchGuard(ttl) if dispatch_guard is None else dispatch_guard
        self.receipts = ReceiptChain()
        self.metrics = Metrics()
        self._lock = threading.RLock()

    def close(self) -> None:
        for component in (self.pre_authority, self.authority):
            close = getattr(component, "close", None)
            if callable(close):
                close()

    def _check_chain(self) -> None:
        if not self.receipts.assert_intact():
            raise ReceiptIntegrityError("RECEIPT_CHAIN_INVALID")

    def run(self, scenario: str = "allow") -> DispatchResult:
        with self._lock:
            self._check_chain()
            return self._run(scenario)

    @staticmethod
    def _held(decision: AuthorityDecision, reason: str) -> AuthorityDecision:
        return replace(decision, verdict=Verdict.HOLD, authorized_action=None,
                       reason_codes=[*decision.reason_codes, reason])

    @staticmethod
    def _local_hold(evidence: EvidenceFrame, action: ProposedAction, reason: str) -> AuthorityDecision:
        return AuthorityDecision("failure-" + action.action_id, Verdict.HOLD, [reason], action,
                                 None, evidence, int(time.time() * 1000), 0.0, "pipeline-local-failure-v1")

    def _failure(self, reason: str, start: int) -> DispatchResult:
        evidence = EvidenceFrame.fresh(confidence=0.0, workspace_clear=False,
            metadata={"provider": "pipeline-error", "observation_available": False})
        action = ProposedAction.pick_place(evidence.evidence_id, action_type="invalid", speed_mps=0.0, trajectory=[])
        decision = self._local_hold(evidence, action, reason)
        receipt = self.receipts.seal("AUTHORITY_DECISION", decision.to_dict())
        elapsed = (time.perf_counter_ns() - start) / 1e6
        self.metrics.record("HOLD", 0.0, elapsed)
        return DispatchResult(decision, receipt, False,
                              {"status": "NOT_EXECUTED", "reason": reason}, None, elapsed, False)

    def _evaluate_checked(self, evidence: EvidenceFrame, action: ProposedAction) -> AuthorityDecision:
        safe_evidence, safe_action = evidence, action
        authority_evidence, authority_action = copy_evidence(safe_evidence), copy_action(safe_action)
        try:
            received = self.authority.evaluate(authority_evidence, authority_action)
            if authority_evidence != safe_evidence or authority_action != safe_action:
                return self._local_hold(safe_evidence, safe_action, "AUTHORITY_INPUT_MUTATED")
            decision = copy_decision(received)
            if decision.evidence != safe_evidence or decision.original_action != safe_action:
                return self._local_hold(safe_evidence, safe_action, "AUTHORITY_BINDING_CHANGED")
            if safe_action.evidence_id != safe_evidence.evidence_id and decision.verdict in {Verdict.ALLOW, Verdict.TRANSFORM}:
                return self._held(decision, "EVIDENCE_BINDING_MISMATCH")
            return decision
        except Exception:
            return self._local_hold(safe_evidence, safe_action, "AUTHORITY_DECISION_INVALID")

    def _apply_pre_authority(self, evidence: EvidenceFrame, action: ProposedAction
                             ) -> tuple[ProposedAction, dict | None, str | None]:
        """Attach derived evidence without granting or changing execution authority."""
        provider = self.pre_authority
        if provider is None:
            return action, None, None

        # The planner cannot pre-populate the reserved evidence slot. A forged
        # sponsor claim must never be allowed to reach Gatekeeper as trusted data.
        if "pre_authority_evidence" in action.metadata:
            record = {"schema": "oasse.pre-authority-evidence.v1", "provider": getattr(provider, "name", "unknown"),
                      "status": "REJECTED", "authority": False,
                      "required": bool(getattr(provider, "required", False)),
                      "error_code": "PRE_AUTHORITY_METADATA_RESERVED"}
            return action, record, "PRE_AUTHORITY_METADATA_RESERVED"

        safe_evidence, safe_action = copy_evidence(evidence), copy_action(action)
        provider_evidence, provider_action = copy_evidence(safe_evidence), copy_action(safe_action)
        try:
            derived = provider.derive(provider_evidence, provider_action)
            if provider_evidence != safe_evidence or provider_action != safe_action:
                raise TenkiEvidenceError("PRE_AUTHORITY_INPUT_MUTATED")
            record = plain(derived, max_depth=16, max_nodes=4096)
            if not isinstance(record, dict) or record.get("authority") is not False:
                raise TenkiEvidenceError("PRE_AUTHORITY_EVIDENCE_INVALID")
            name = getattr(provider, "name", None)
            if not isinstance(name, str) or not name:
                raise TenkiEvidenceError("PRE_AUTHORITY_PROVIDER_INVALID")
            enriched_metadata = dict(copy_action(safe_action).metadata)
            enriched_metadata["pre_authority_evidence"] = {name: record}
            enriched = replace(safe_action, metadata=enriched_metadata)
            validate_inputs(safe_evidence, enriched)
            # No executable field, identity field, or evidence binding may be
            # changed by a derived-evidence provider.
            for field in ("action_id", "actor_id", "action_type", "target_bin", "speed_mps",
                          "evidence_id", "requested_at_ms", "object_id", "trajectory"):
                if getattr(enriched, field) != getattr(safe_action, field):
                    raise TenkiEvidenceError("PRE_AUTHORITY_ACTION_CHANGED")
            return copy_action(enriched), record, None
        except TenkiEvidenceError as exc:
            code = exc.code
        except Exception:
            code = "PRE_AUTHORITY_EVIDENCE_INVALID"

        required = bool(getattr(provider, "required", False))
        failure = {
            "schema": "oasse.pre-authority-evidence.v1",
            "provider": getattr(provider, "name", "unknown"),
            "status": "UNAVAILABLE",
            "authority": False,
            "required": required,
            "error_code": code,
        }
        return safe_action, failure, code if required else None

    def _evaluate_with_pre_authority(self, evidence: EvidenceFrame, action: ProposedAction
                                     ) -> AuthorityDecision:
        enriched, record, reason = self._apply_pre_authority(evidence, action)
        if record is not None:
            self.receipts.seal("PRE_AUTHORITY_EVIDENCE", record)
        if reason is not None:
            return self._local_hold(evidence, enriched, reason)
        return self._evaluate_checked(evidence, enriched)

    def evaluate_only(self, evidence: EvidenceFrame, action: ProposedAction) -> AuthorityDecision:
        with self._lock:
            self._check_chain()
            validate_inputs(evidence, action)
            start = time.perf_counter_ns()
            decision = self._evaluate_with_pre_authority(copy_evidence(evidence), copy_action(action))
            self.receipts.seal("AUTHORITY_DECISION", decision.to_dict())
            self.metrics.record(decision.verdict.value, decision.authority_latency_ms,
                                (time.perf_counter_ns() - start) / 1e6)
            return decision

    def _guard_reason(self, evidence: EvidenceFrame, action: ProposedAction, deadline: int,
                      *, reserve: bool = False) -> str | None:
        try:
            if reserve:
                return self.dispatch_guard.reserve(evidence, action, deadline)
            return self.dispatch_guard.check(evidence, action, deadline)
        except Exception:
            return "DISPATCH_CHECK_FAILED"

    def _invoke(self, decision: AuthorityDecision, deadline: int) -> tuple[bool, dict]:
        expected = decision.authorized_action
        sent = copy_action(expected)
        evidence = decision.evidence

        def check_step() -> str | None:
            try:
                if sent != expected:
                    return "AUTHORIZED_ACTION_CHANGED"
                return self.dispatch_guard.freshness(evidence, deadline)
            except Exception:
                return "DISPATCH_CHECK_FAILED"

        try:
            guarded = getattr(self.actuator, "execute_guarded", None)
            raw = guarded(sent, check_step) if callable(guarded) else self.actuator.execute(sent)
            result = plain(raw)
            if not isinstance(result, dict):
                raise TypeError("actuator result must be an object")
            status = result.get("status", "UNKNOWN")
            if type(status) is not str or status not in {"EXECUTED", "NOT_EXECUTED", "FAILED", "UNKNOWN"}:
                status = "UNKNOWN"
            result["status"] = status
            acknowledged = result.get("action_id")
            if (acknowledged is not None and acknowledged != sent.action_id) or (status == "EXECUTED" and acknowledged != sent.action_id):
                result = {"status": "UNKNOWN", "reason": "ACTUATOR_RESULT_BINDING_MISMATCH"}
            elif sent != expected and status == "EXECUTED":
                result = {"status": "UNKNOWN", "reason": "AUTHORIZED_ACTION_CHANGED"}
            return result["status"] == "EXECUTED", result
        except Exception as exc:
            return False, {"status": "UNKNOWN", "reason": "ACTUATOR_ERROR", "error_type": type(exc).__name__}

    def _run(self, scenario: str) -> DispatchResult:
        start = time.perf_counter_ns()
        try:
            observed = self.perception.observe(scenario)
            validate_inputs(observed)
            evidence = copy_evidence(observed)
            deadline = self.dispatch_guard.deadline(evidence)
        except Exception:
            return self._failure("PERCEPTION_INVALID", start)
        try:
            planner_evidence = copy_evidence(evidence)
            proposed = self.vla.propose(planner_evidence, scenario)
            if planner_evidence != evidence:
                return self._failure("EVIDENCE_CHANGED_BY_PLANNER", start)
            validate_inputs(evidence, proposed)
            action = copy_action(proposed)
        except Exception:
            return self._failure("PROPOSAL_INVALID", start)

        action, pre_record, pre_reason = self._apply_pre_authority(evidence, action)
        if pre_record is not None:
            self.receipts.seal("PRE_AUTHORITY_EVIDENCE", pre_record)
        decision = (self._local_hold(evidence, action, pre_reason)
                    if pre_reason is not None else self._evaluate_checked(evidence, action))
        dispatchable = executable(decision)
        if dispatchable:
            reason = self._guard_reason(evidence, action, deadline)
            if reason:
                decision, dispatchable = self._held(decision, reason), False
        receipt = self.receipts.seal("AUTHORITY_DECISION", decision.to_dict())
        attempted = executed = False
        outcome = None
        result = {"status": "NOT_EXECUTED", "reason": decision.verdict.value}
        if dispatchable:
            self._check_chain()
            reason = self._guard_reason(evidence, action, deadline, reserve=True)
            if reason:
                decision = self._held(decision, reason)
                receipt = self.receipts.seal("AUTHORITY_DECISION", decision.to_dict())
                result = {"status": "NOT_EXECUTED", "reason": reason}
            else:
                attempted = True
                executed, result = self._invoke(decision, deadline)
                outcome = self.receipts.seal("PHYSICAL_OUTCOME", {
                    "decision_receipt_hash": receipt.receipt_hash,
                    "decision_id": decision.decision_id,
                    "authorized_action_id": decision.authorized_action.action_id,
                    "dispatch_attempted": True, "execution_confirmed": executed, "actuator_result": result})
        elif decision.verdict == Verdict.TRANSFORM:
            reason = "TRANSFORM_WITHOUT_AUTHORIZED_ACTION" if decision.authorized_action is None else "TRANSFORM_WITHOUT_AUTHORIZED_CHANGE"
            result = {"status": "NOT_EXECUTED", "reason": reason}
        elapsed = (time.perf_counter_ns() - start) / 1e6
        self.metrics.record(decision.verdict.value, decision.authority_latency_ms, elapsed)
        return DispatchResult(decision, receipt, executed, result, outcome, elapsed, attempted)
