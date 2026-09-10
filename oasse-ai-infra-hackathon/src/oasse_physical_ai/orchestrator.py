from __future__ import annotations

import time
from typing import Optional

from .gatekeeper_client import AuthorityClient, build_authority_client
from .metrics import Metrics
from .models import DispatchResult, Verdict
from .receipts import ReceiptChain
from .providers.actuator import SimulatedActuator
from .providers.perception import MockPerceptionProvider
from .providers.vla import MockVLAProvider


class PhysicalAIOrchestrator:
    def __init__(self, authority: Optional[AuthorityClient] = None) -> None:
        self.authority = authority or build_authority_client()
        self.perception = MockPerceptionProvider()
        self.vla = MockVLAProvider()
        self.actuator = SimulatedActuator()
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

        if decision.verdict in {Verdict.ALLOW, Verdict.TRANSFORM} and decision.authorized_action is not None:
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
