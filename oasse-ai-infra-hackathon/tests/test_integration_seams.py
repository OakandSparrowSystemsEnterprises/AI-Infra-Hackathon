import hashlib
import time
import unittest

from oasse_physical_ai.models import EvidenceFrame
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine
from oasse_physical_ai.providers.lerobot_mujoco import LeRobotVLAProvider, MuJoCoActuator
from oasse_physical_ai.providers.openvino_adapter import CapturedFrame, OpenVINOPerceptionProvider
from oasse_physical_ai.providers.perception import frame_sha256


class StaticFrameSource:
    def __init__(self, frame):
        self.frame = frame

    def capture(self):
        return self.frame


class FixedPerception:
    def __init__(self, evidence):
        self.evidence = evidence

    def observe(self, scenario="allow"):
        return self.evidence


class FakeScalar:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value


class FakeArray:
    def __init__(self, value):
        self.value = value

    def tolist(self):
        return self.value


class IntegrationSeamTests(unittest.TestCase):
    def test_frame_hash_is_content_derived(self):
        self.assertEqual(frame_sha256(b"frame-a"), hashlib.sha256(b"frame-a").hexdigest())
        self.assertNotEqual(frame_sha256(b"frame-a"), frame_sha256(b"frame-b"))

    def test_openvino_provider_normalizes_evidence(self):
        frame = CapturedFrame(b"camera-frame", 1_700_000_000_000, "intel-camera", 42)

        def infer(_data):
            return {
                "confidence": FakeScalar(0.97),
                "workspace_clear": True,
                "anomaly_score": FakeScalar(0.91),
                "target_label": "defective_cube",
                "anomaly_bbox_xyxy": FakeArray([0.1, 0.2, 0.4, 0.5]),
                "object_pose_xyzrpy": FakeArray([0.2, 0.0, 0.03, 0.0, 0.0, 0.0]),
                "object_dimensions_xyz": [0.04, 0.04, 0.04],
                "metadata": {"model": "anomaly-detector"},
            }

        evidence = OpenVINOPerceptionProvider(StaticFrameSource(frame), infer).observe()
        self.assertEqual(evidence.frame_hash, hashlib.sha256(b"camera-frame").hexdigest())
        self.assertEqual(evidence.camera_id, "intel-camera")
        self.assertEqual(evidence.frame_sequence, 42)
        self.assertEqual(evidence.anomaly_bbox_xyxy, [0.1, 0.2, 0.4, 0.5])
        self.assertEqual(evidence.object_pose_xyzrpy, [0.2, 0.0, 0.03, 0.0, 0.0, 0.0])
        self.assertEqual(evidence.metadata["provider"], "openvino")
        self.assertEqual(evidence.metadata["model"], "anomaly-detector")

    def test_openvino_provider_preserves_capture_time_for_freshness(self):
        captured = int(time.time() * 1000) - 5_000
        frame = CapturedFrame(b"stale-frame", captured)
        provider = OpenVINOPerceptionProvider(
            StaticFrameSource(frame),
            lambda _: {"confidence": 0.99, "workspace_clear": True, "anomaly_score": 0.0},
        )
        self.assertEqual(provider.observe().captured_at_ms, captured)

    def test_openvino_provider_rejects_nonfinite_output(self):
        frame = CapturedFrame(b"frame", int(time.time() * 1000))
        provider = OpenVINOPerceptionProvider(
            StaticFrameSource(frame),
            lambda _: {"confidence": float("nan"), "workspace_clear": True, "anomaly_score": 0.0},
        )
        with self.assertRaises(ValueError):
            provider.observe()

    def test_lerobot_provider_binds_proposal_to_exact_evidence(self):
        evidence = EvidenceFrame.fresh(frame_hash="abc123")
        provider = LeRobotVLAProvider(
            lambda _: {
                "target_bin": "reject",
                "speed_mps": 0.25,
                "trajectory": [[0.0, 0.0, 0.0], [0.1, 0.2, 0.3]],
            },
            model_name="smolvla",
        )
        action = provider.propose(evidence)
        self.assertEqual(action.evidence_id, evidence.evidence_id)
        self.assertEqual(action.target_bin, "reject")
        self.assertEqual(action.metadata["source_frame_hash"], "abc123")
        self.assertEqual(action.metadata["model"], "smolvla")

    def test_mujoco_actuator_receives_only_authorized_action(self):
        calls = []

        def execute(action):
            calls.append(action)
            return {"sim_state": "advanced"}

        evidence = EvidenceFrame.fresh(
            confidence=0.99,
            workspace_clear=True,
            anomaly_score=0.0,
            frame_hash="fresh",
        )
        vla = LeRobotVLAProvider(lambda _: {"speed_mps": 0.20, "target_bin": "accept"})
        orch = PhysicalAIOrchestrator(
            authority=ReferenceAuthorityEngine(),
            perception=FixedPerception(evidence),
            vla=vla,
            actuator=MuJoCoActuator(execute),
        )
        result = orch.run()
        self.assertTrue(result.executed)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], result.decision.authorized_action)
        self.assertEqual(result.actuator_result["sim_state"], "advanced")

    def test_stale_real_evidence_never_reaches_mujoco(self):
        calls = []
        stale = EvidenceFrame.fresh(
            captured_at_ms=int(time.time() * 1000) - 5_000,
            confidence=0.99,
            workspace_clear=True,
            frame_hash="stale",
        )
        orch = PhysicalAIOrchestrator(
            authority=ReferenceAuthorityEngine(evidence_max_age_ms=500),
            perception=FixedPerception(stale),
            vla=LeRobotVLAProvider(lambda _: {"speed_mps": 0.20, "target_bin": "accept"}),
            actuator=MuJoCoActuator(lambda action: calls.append(action) or {"status": "EXECUTED"}),
        )
        result = orch.run()
        self.assertFalse(result.executed)
        self.assertEqual(calls, [])
        self.assertEqual(result.decision.verdict.value, "HOLD")
        self.assertTrue(orch.receipts.verify())

    def test_perception_and_vla_are_constructor_injectable(self):
        evidence = EvidenceFrame.fresh(frame_hash="injected")
        perception = FixedPerception(evidence)
        vla = LeRobotVLAProvider(lambda _: {"speed_mps": 0.20, "target_bin": "accept"})
        actuator = MuJoCoActuator(lambda _: {"status": "EXECUTED"})
        orch = PhysicalAIOrchestrator(
            authority=ReferenceAuthorityEngine(),
            perception=perception,
            vla=vla,
            actuator=actuator,
        )
        self.assertIs(orch.perception, perception)
        self.assertIs(orch.vla, vla)
        self.assertIs(orch.actuator, actuator)


if __name__ == "__main__":
    unittest.main()
