from __future__ import annotations

import time
from typing import Optional

from .gatekeeper_client import AuthorityClient, build_authority_client
from .metrics import Metrics
from .models import AuthorityDecision, DispatchResult, Verdict, physically_changed
from .receipts import ReceiptChain
from .providers.actuator import Actuator, SimulatedActuator
from .providers.perception import MockPerceptionProvider, PerceptionProvider
from .providers.vla import MockVLAProvider, VLAProvider


def executable(decision: AuthorityDecision) -> bool:
    """Only an authorized action may reach the actuator.

    ALLOW executes the proposal. TRANSFORM executes the authorized action and
    only if it differs from the proposal in a physical field: the original
    proposal is never executed under TRANSFORM, whichever engine produced
    the decision.
    """
    if decision.verdict not in {Verdict.ALLOW, Verdict.TRANSFORM} or decision.authorized_action is None:
        return False
    if decision.verdict == Verdict.TRANSFORM and not physically_changed(decision.authorized_action, decision.original_action):
        return False
    return True


class PhysicalAIOrchestrator:
    def __init__(
        self,
        authority: Optional[AuthorityClient] = None,
        perception: Optional[PerceptionProvider] = None,
        vla: Optional[VLAProvider] = None,
        actuator: Optional[Actuator] = None,
    ) -> None:
        self.authority = authority or build_authority_client()
        self.perception = perception or MockPerceptionProvider()
        self.vla = vla or MockVLAProvider()
        self.actuator = actuator or SimulatedActuator()
        self.receipts = ReceiptChain()
        self.metrics = Metrics()

    def run(self, scenario: str = "allow") -> DispatchResult:
        start = time.perf_counter_ns()
        evidence = self.perception.observe(scenario)
        action = self.vla.propose(evidence, scenario)
        decision = self.authority.evaluate(evidence, action)

        decision_receipt = self.receipts.seal("AUTHORITY_DECISION", decision.to_dict())
        executed = False
        actuator_result = {"status": "NOT_EXECUTED", "reason": decision.verdict.value}
        outcome_receipt = None

        if executable(decision):
            actuator_result = self.actuator.execute(decision.authorized_action)
            executed = True
            outcome_receipt = self.receipts.seal(
                "PHYSICAL_OUTCOME",
                {
                    "decision_receipt_hash": decision_receipt.receipt_hash,
                    "decision_id": decision.decision_id,
                    "authorized_action_id": decision.authorized_action.action_id,
                    "actuator_result": actuator_result,
                },
            )
        elif decision.verdict == Verdict.TRANSFORM:
            reason = "TRANSFORM_WITHOUT_AUTHORIZED_ACTION" if decision.authorized_action is None else "TRANSFORM_WITHOUT_AUTHORIZED_CHANGE"
            actuator_result = {"status": "NOT_EXECUTED", "reason": reason}

        total_ms = (time.perf_counter_ns() - start) / 1_000_000.0
        self.metrics.record(decision.verdict.value, decision.authority_latency_ms, total_ms)
        return DispatchResult(
            decision=decision,
            decision_receipt=decision_receipt,
            executed=executed,
            actuator_result=actuator_result,
            outcome_receipt=outcome_receipt,
            total_latency_ms=total_ms,
        )
