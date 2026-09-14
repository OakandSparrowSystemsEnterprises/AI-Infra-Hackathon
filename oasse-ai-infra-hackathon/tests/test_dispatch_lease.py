from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import time

from oasse_physical_ai.dispatch import DispatchGuard
from oasse_physical_ai.models import EvidenceFrame, ProposedAction, Verdict
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine


def test_monotonic_lease_expires_even_when_wall_clock_does_not_advance():
    wall = int(time.time()*1000)
    monotonic = [0]
    guard = DispatchGuard(clock_ms=lambda: wall, monotonic_ns=lambda: monotonic[0])
    evidence = EvidenceFrame.fresh(captured_at_ms=wall)
    deadline = guard.deadline(evidence)
    monotonic[0] = 501000000
    assert guard.freshness(evidence, deadline) == "EVIDENCE_LEASE_EXPIRED"


def test_monotonic_lease_is_captured_before_authority_wait():
    wall = int(time.time()*1000)
    monotonic = [0]
    evidence = EvidenceFrame.fresh(captured_at_ms=wall)
    class Perception:
        def observe(self, scenario="allow"): return evidence
    class Authority:
        def evaluate(self, ev, action):
            decision = ReferenceAuthorityEngine().evaluate(ev, action, now_ms=wall)
            monotonic[0] += 501000000
            return decision
    calls = []
    class Actuator:
        def execute(self, action): calls.append(action); return {"status":"EXECUTED"}
    orch = PhysicalAIOrchestrator(authority=Authority(), perception=Perception(), actuator=Actuator(),
        dispatch_guard=DispatchGuard(clock_ms=lambda:wall, monotonic_ns=lambda:monotonic[0]))
    result = orch.run()
    assert result.decision.verdict == Verdict.HOLD
    assert "EVIDENCE_LEASE_EXPIRED" in result.decision.reason_codes and not calls


def test_shared_guard_reservation_is_atomic():
    now = int(time.time()*1000)
    guard = DispatchGuard(clock_ms=lambda: now)
    evidence = EvidenceFrame.fresh(captured_at_ms=now)
    action = ProposedAction.pick_place(evidence.evidence_id)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: guard.reserve(evidence, action), range(32)))
    assert results.count(None) == 1
    assert results.count("EVIDENCE_OR_ACTION_REPLAYED") == 31
