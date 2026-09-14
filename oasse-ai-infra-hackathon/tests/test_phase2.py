from dataclasses import replace
import hashlib
import json
import time

import numpy as np
import pytest

from oasse_physical_ai.dispatch import DispatchGuard
from oasse_physical_ai.models import EvidenceFrame, ProposedAction, Verdict
from oasse_physical_ai.normalization import plain
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine
from oasse_physical_ai.providers.lerobot_mujoco import LeRobotVLAProvider, MuJoCoActuator
from oasse_physical_ai.providers.openvino_adapter import CapturedFrame, OpenVINOPerceptionProvider


def proposal(**values):
    return {"action_type": "pick_place", "object_id": "cube-1", "target_bin": "accept",
            "speed_mps": 0.2, "trajectory": [[0., 0., 0.], [0.1, 0., 0.1]], **values}


class Fixed:
    def __init__(self, evidence):
        self.evidence = evidence
    def observe(self, scenario="allow"):
        return self.evidence


class Frame:
    def __init__(self, data=b"pixels", captured=None, sequence=1):
        self.value = CapturedFrame(data, captured if captured is not None else int(time.time()*1000), "test-camera", sequence)
    def capture(self):
        return self.value


def infer(**values):
    return {"confidence": .99, "workspace_clear": True, "anomaly_score": .02, **values}


def make_orch(evidence=None, **kwargs):
    source = Fixed(evidence or EvidenceFrame.fresh())
    calls = []
    def execute(action):
        calls.append(action)
        return {"status": "EXECUTED", "action_id": action.action_id}
    options = {"authority": ReferenceAuthorityEngine(), "perception": source,
               "vla": LeRobotVLAProvider(lambda _: proposal()), "actuator": MuJoCoActuator(execute)}
    options.update(kwargs)
    return PhysicalAIOrchestrator(**options), source, calls


def test_real_numpy_vectors_and_scalars():
    p = OpenVINOPerceptionProvider(Frame(), lambda _: infer(
        confidence=np.float32(.97), anomaly_bbox_xyxy=np.array([.1,.2,.4,.5]),
        object_pose_xyzrpy=np.zeros(6), object_dimensions_xyz=np.full(3, .04),
        metadata={"nested": np.array([[1,2],[3,4]]), "counter": np.int64(42)}))
    evidence = p.observe()
    assert evidence.anomaly_bbox_xyxy == [.1,.2,.4,.5]
    assert evidence.object_pose_xyzrpy == [0.]*6
    assert type(evidence.confidence) is float
    json.dumps(evidence.__dict__, allow_nan=False)


@pytest.mark.parametrize("key", ["workspace_clear", "confidence", "anomaly_score"])
def test_missing_observation_is_not_invented(key):
    output = infer(); del output[key]
    provider = OpenVINOPerceptionProvider(Frame(), lambda _: output)
    with pytest.raises(ValueError): provider.observe()
    orch, _, calls = make_orch(perception=provider)
    result = orch.run()
    assert result.decision.verdict == Verdict.HOLD
    assert not result.dispatch_attempted and not calls
    assert result.decision.reason_codes == ["PERCEPTION_INVALID"]
    assert len(orch.receipts.all()) == 1 and orch.receipts.verify()


@pytest.mark.parametrize("key", list(proposal()))
def test_missing_motion_is_not_invented(key):
    output = proposal(); del output[key]
    vla = LeRobotVLAProvider(lambda _: output)
    with pytest.raises(ValueError): vla.propose(EvidenceFrame.fresh())
    orch, _, calls = make_orch(vla=vla)
    result = orch.run()
    assert result.decision.reason_codes == ["PROPOSAL_INVALID"]
    assert not result.dispatch_attempted and not calls
    assert orch.receipts.verify()


def test_empty_policy_is_a_hold():
    orch, _, calls = make_orch(vla=LeRobotVLAProvider(lambda _: {}))
    result = orch.run()
    assert result.decision.verdict == Verdict.HOLD and not result.executed and not calls


@pytest.mark.parametrize("value", [True, False, "0.2", float("nan"), float("inf"), -1.0])
def test_invalid_policy_speed(value):
    with pytest.raises((TypeError, ValueError)):
        LeRobotVLAProvider(lambda _: proposal(speed_mps=value)).propose(EvidenceFrame.fresh())


def test_numpy_policy_output():
    action = LeRobotVLAProvider(lambda _: proposal(speed_mps=np.float32(.2), trajectory=np.array([[0,0,0],[.1,0,.1]]))).propose(EvidenceFrame.fresh())
    assert type(action.speed_mps) is float and isinstance(action.trajectory, list)


def test_capture_copied_before_inference():
    buffer = bytearray(b"original")
    source = Frame(buffer)
    def change(data):
        assert data == b"original"
        buffer[:] = b"modified"
        return infer()
    evidence = OpenVINOPerceptionProvider(source, change).observe()
    assert evidence.frame_hash == hashlib.sha256(b"original").hexdigest()


@pytest.mark.parametrize("captured", [True, -1, "123", 1.5])
def test_capture_timestamp_strict(captured):
    with pytest.raises((TypeError, ValueError)):
        OpenVINOPerceptionProvider(Frame(captured=captured), lambda _: infer()).observe()


@pytest.mark.parametrize("values", [
    {"anomaly_bbox_xyxy": [.8,.2,.1,.4]}, {"anomaly_bbox_xyxy": [-1,0,1,1]},
    {"object_dimensions_xyz": [.1,0,.1]}, {"object_pose_xyzrpy": [0]*5},
    {"workspace_clear": "false"}, {"confidence": True}])
def test_invalid_geometry_or_observation(values):
    with pytest.raises((TypeError, ValueError)):
        OpenVINOPerceptionProvider(Frame(), lambda _: infer(**values)).observe()


def test_normalizer_rejects_cycles_and_budget_exhaustion():
    cyclic = []; cyclic.append(cyclic)
    with pytest.raises(ValueError): plain(cyclic)
    with pytest.raises(ValueError): plain(list(range(100)), max_nodes=10)
    deep = []; root = deep
    for _ in range(40): nxt=[]; deep.append(nxt); deep=nxt
    with pytest.raises(ValueError): plain(root)


def test_future_dated_reference_frame_is_held():
    now = int(time.time()*1000)
    ev = EvidenceFrame.fresh(captured_at_ms=now+1)
    decision = ReferenceAuthorityEngine().evaluate(ev, ProposedAction.pick_place(ev.evidence_id), now_ms=now)
    assert decision.verdict == Verdict.HOLD and "EVIDENCE_IN_FUTURE" in decision.reason_codes


def test_expiry_during_authority_call():
    clock = [int(time.time()*1000)]
    ev = EvidenceFrame.fresh(captured_at_ms=clock[0])
    class Delayed:
        def evaluate(self, evidence, action):
            answer = ReferenceAuthorityEngine().evaluate(evidence, action, now_ms=clock[0])
            clock[0] += 501
            return answer
    orch, _, calls = make_orch(ev, authority=Delayed(), dispatch_guard=DispatchGuard(clock_ms=lambda: clock[0]))
    result = orch.run()
    assert result.decision.verdict == Verdict.HOLD
    assert "EVIDENCE_EXPIRED_AT_DISPATCH" in result.decision.reason_codes and not calls
    assert orch.receipts.verify()


def test_expiry_during_receipt_seal():
    now = int(time.time()*1000); clock=[now]
    orch, _, calls = make_orch(EvidenceFrame.fresh(captured_at_ms=now), dispatch_guard=DispatchGuard(clock_ms=lambda: clock[0]))
    seal = orch.receipts.seal
    def delayed_seal(*args):
        answer=seal(*args); clock[0] += 501; return answer
    orch.receipts.seal = delayed_seal
    result=orch.run()
    assert result.decision.verdict == Verdict.HOLD and not calls
    assert len(orch.receipts.all()) == 2 and orch.receipts.verify()


def test_reused_evidence_cannot_dispatch_twice():
    orch, _, calls = make_orch()
    assert orch.run().executed
    result = orch.run()
    assert not result.dispatch_attempted and result.decision.verdict == Verdict.HOLD
    assert "EVIDENCE_OR_ACTION_REPLAYED" in result.decision.reason_codes
    assert len(calls) == 1


def test_static_scene_with_new_capture_sequence_is_not_replay():
    ev=EvidenceFrame.fresh(frame_sequence=10, frame_hash="same-pixels")
    orch, source, calls = make_orch(ev)
    assert orch.run().executed
    source.evidence=replace(ev,evidence_id="new-capture",frame_sequence=11)
    assert orch.run().executed and len(calls)==2


def test_sequence_reuse_under_new_id_is_held():
    ev=EvidenceFrame.fresh(frame_sequence=10)
    orch, source, calls=make_orch(ev)
    assert orch.run().executed
    source.evidence=replace(ev,evidence_id="new-id")
    result=orch.run()
    assert "FRAME_SEQUENCE_REUSED" in result.decision.reason_codes and len(calls)==1


def test_scene_change_after_observation_blocks_dispatch():
    ev=EvidenceFrame.fresh(scene_hash="observed-scene")
    orch, _, calls=make_orch(ev,dispatch_guard=DispatchGuard(scene_hash=lambda:"different-scene"))
    result=orch.run()
    assert "SCENE_CHANGED" in result.decision.reason_codes and not calls


@pytest.mark.parametrize("status", [None, "NOT_EXECUTED", "FAILED", "UNKNOWN", "unrecognized"])
def test_no_manufactured_execution_success(status):
    def callback(_): return {} if status is None else {"status":status}
    orch, _, _=make_orch(actuator=MuJoCoActuator(callback))
    result=orch.run()
    assert result.dispatch_attempted and not result.executed
    assert result.outcome_receipt is not None and orch.receipts.verify()


def test_exception_after_dispatch_is_unknown_not_not_executed():
    calls=[]
    def bad(action): calls.append(action); raise RuntimeError("potential secret")
    orch, _, _=make_orch(actuator=MuJoCoActuator(bad))
    result=orch.run()
    assert result.dispatch_attempted and not result.executed and len(calls)==1
    assert result.actuator_result["status"]=="UNKNOWN"
    assert "potential secret" not in json.dumps(result.to_dict())
    assert result.outcome_receipt is not None and orch.receipts.verify()
    assert not orch.run().dispatch_attempted and len(calls)==1


def test_planner_cannot_mutate_bound_evidence():
    def tamper(ev): ev.metadata["modified"]=True; return proposal()
    orch, _, calls=make_orch(vla=LeRobotVLAProvider(tamper))
    result=orch.run()
    assert result.decision.reason_codes==["EVIDENCE_CHANGED_BY_PLANNER"] and not calls


def test_falsey_injected_provider_is_not_replaced_with_mock():
    class Falsey(Fixed):
        def __bool__(self): return False
    source=Falsey(EvidenceFrame.fresh())
    orch, _, _=make_orch(perception=source)
    assert orch.perception is source and orch.run().executed
