"""Adversarial regression tests for the post-Phase-2 execution boundary."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import json
import time

import pytest
from fastapi.testclient import TestClient

from oasse_physical_ai import api
from oasse_physical_ai.dispatch import DispatchGuard
from oasse_physical_ai.models import EvidenceFrame, ProposedAction, Verdict
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine
from oasse_physical_ai.receipts import ReceiptChain


class FixedPerception:
    def __init__(self, evidence): self.evidence = evidence
    def observe(self, scenario="allow"): return self.evidence


class FixedPlanner:
    def __init__(self, action): self.action = action
    def propose(self, evidence, scenario="allow"): return self.action


class RecordingActuator:
    def __init__(self): self.calls = []
    def execute(self, action):
        self.calls.append(asdict(action))
        return {"status": "EXECUTED", "action_id": action.action_id}


def fixture(**kwargs):
    evidence = EvidenceFrame.fresh(); action = ProposedAction.pick_place(evidence.evidence_id)
    actuator = RecordingActuator()
    options = dict(authority=ReferenceAuthorityEngine(), perception=FixedPerception(evidence),
                   vla=FixedPlanner(action), actuator=actuator)
    options.update(kwargs)
    return PhysicalAIOrchestrator(**options), evidence, action, actuator


def test_seal_time_alias_mutation_cannot_change_dispatched_motion():
    orch, _, action, actuator = fixture(); seal = orch.receipts.seal
    def mutating_seal(kind, payload):
        result = seal(kind, payload)
        if kind == "AUTHORITY_DECISION": action.trajectory[1][0] = 90.0
        return result
    orch.receipts.seal = mutating_seal
    result = orch.run()
    if result.executed:
        sealed = result.decision_receipt.payload["authorized_action"]
        assert actuator.calls[0]["trajectory"] == sealed["trajectory"]
        assert actuator.calls[0]["trajectory"][1][0] == .2
    assert orch.receipts.verify()


def test_midstep_motion_mutation_revokes_guard():
    class MutatingRuntime:
        def execute_guarded(self, action, check):
            action.trajectory[1][0] = 90.0
            reason = check()
            assert reason is not None, "step guard checked time but not bound motion"
            return {"status": "NOT_EXECUTED", "reason": reason}
    orch, _, _, _ = fixture(actuator=MutatingRuntime()); result = orch.run()
    assert result.actuator_result["status"] == "NOT_EXECUTED"
    assert result.actuator_result["reason"] == "AUTHORIZED_ACTION_CHANGED"
    assert not result.executed and orch.receipts.verify()


@pytest.mark.parametrize("field,value", [("speed_mps", True), ("speed_mps", -1), ("trajectory", None),
    ("trajectory", [[0, 0], [1, 1]]), ("actor_id", 1)])
def test_direct_api_rejects_invalid_action(field, value, monkeypatch):
    monkeypatch.setattr(api, "orchestrator", PhysicalAIOrchestrator())
    ev = EvidenceFrame.fresh(); action = asdict(ProposedAction.pick_place(ev.evidence_id)); action[field] = value
    with TestClient(api.app, raise_server_exceptions=False) as client:
        response = client.post("/v1/evaluate", json={"evidence": asdict(ev), "action": action})
    assert response.status_code in {400, 422}, response.text


@pytest.mark.parametrize("field,value", [("confidence", True), ("workspace_clear", "yes"),
    ("captured_at_ms", "yesterday"), ("object_dimensions_xyz", [-1, .1, .1]),
    ("anomaly_bbox_xyxy", [.8,.1,.2,.5]), ("metadata", []), ("scene_hash", {"bad": "shape"})])
def test_direct_api_rejects_invalid_evidence(field, value, monkeypatch):
    monkeypatch.setattr(api, "orchestrator", PhysicalAIOrchestrator())
    ev = EvidenceFrame.fresh(); evidence = asdict(ev); evidence[field] = value
    with TestClient(api.app, raise_server_exceptions=False) as client:
        response = client.post("/v1/evaluate", json={"evidence": evidence,
            "action": asdict(ProposedAction.pick_place(ev.evidence_id))})
    assert response.status_code in {400, 422}, response.text


def test_evaluate_only_seals_without_actuating(monkeypatch):
    orch, ev, action, actuator = fixture(); monkeypatch.setattr(api, "orchestrator", orch)
    with TestClient(api.app) as client:
        response = client.post("/v1/evaluate", json={"evidence": asdict(ev), "action": asdict(action)})
    assert response.status_code == 200 and response.json()["verdict"] == "ALLOW"
    assert len(orch.receipts.all()) == 1 and not actuator.calls and orch.receipts.verify()


def test_receipt_does_not_alias_caller_payload():
    payload = {"trajectory": [[1, 2, 3]]}; chain = ReceiptChain(); receipt = chain.seal("TEST", payload)
    payload["trajectory"][0][0] = 100
    assert receipt.payload["trajectory"][0][0] == 1 and chain.verify()


@pytest.mark.parametrize("payload", [{"x": float("nan")}, {"x": {1,2}}, {1: "not a string key"}])
def test_receipts_reject_noncanonical_inputs(payload):
    chain = ReceiptChain()
    with pytest.raises((TypeError, ValueError)): chain.seal("TEST", payload)
    assert not chain.all()


def test_receipt_chain_parallel_append():
    chain = ReceiptChain()
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda n: chain.seal("TEST", {"n": n}), range(200)))
    assert len(chain.all()) == 200 and chain.verify()


def test_public_receipt_mutation_cannot_corrupt_chain_or_future_dispatch():
    orch, _, _, actuator = fixture()
    receipt = orch.receipts.seal("TEST", {"n": 1})
    receipt.payload["n"] = 2
    result = orch.run()
    assert result.executed and len(actuator.calls) == 1
    assert orch.receipts.verify() and orch.receipts.all()[0].payload["n"] == 1


def test_empty_authorized_actor_set_does_not_enable_defaults():
    ev = EvidenceFrame.fresh()
    decision = ReferenceAuthorityEngine(allowed_actors=set()).evaluate(ev, ProposedAction.pick_place(ev.evidence_id))
    assert decision.verdict == Verdict.DENY


def test_invalid_authority_latency_is_not_sealed():
    class BadAuthority:
        def evaluate(self, ev, action):
            return replace(ReferenceAuthorityEngine().evaluate(ev, action), authority_latency_ms=float("nan"))
    orch, _, _, actuator = fixture(authority=BadAuthority()); result = orch.run()
    assert result.decision.verdict == Verdict.HOLD and not actuator.calls
    json.dumps(result.to_dict(), allow_nan=False); assert orch.receipts.verify()


def test_unavailable_scene_check_keeps_original_authority_evidence():
    def unavailable(): raise OSError("do not expose this message")
    orch, ev, action, actuator = fixture(dispatch_guard=DispatchGuard(scene_hash=unavailable))
    orch.perception.evidence = replace(ev, scene_hash="observed")
    result = orch.run()
    assert result.decision.verdict == Verdict.HOLD and not actuator.calls
    assert result.decision.original_action.action_id == action.action_id
    assert "DISPATCH_CHECK_FAILED" in result.decision.reason_codes
    assert "do not expose" not in json.dumps(result.to_dict())
