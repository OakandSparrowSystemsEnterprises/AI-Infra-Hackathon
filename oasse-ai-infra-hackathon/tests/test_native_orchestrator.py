"""Exercise the native perception provider directly inside the orchestrator."""
import os
import pytest
pytest.importorskip("mujoco")
pytest.importorskip("openvino")
if os.environ.get("OASSE_NATIVE_CAMERA_TESTS") != "1":
    pytest.skip("headless native camera job required", allow_module_level=True)

from oasse_physical_ai.dispatch import DispatchGuard
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine
from oasse_physical_ai.providers.lerobot_mujoco import LeRobotVLAProvider
from oasse_physical_ai.providers.mujoco_runtime import MuJoCoCartesianRuntime
from oasse_physical_ai.providers.mujoco_camera import MuJoCoRGBCamera
from oasse_physical_ai.providers.openvino_runtime import (
    RGBSpec, OpenVINOIRRunner, NativeOpenVINOPerception,
    ReferenceDifferenceDecoder, export_reference_difference,
)


@pytest.mark.parametrize("marked", [False, True])
def test_native_capture_and_inference_run_inside_dispatch_pipeline(tmp_path,marked):
    runtime = MuJoCoCartesianRuntime()
    spec = RGBSpec()
    with MuJoCoRGBCamera(runtime,spec) as camera:
        reference = camera.capture()
        model = tmp_path / "reference.xml"
        digest = export_reference_difference(reference.data,spec,model)
        runner = OpenVINOIRRunner(model,spec,expected_sha256=digest)
        runner.infer(reference.data)
        camera.marked = marked
        native = NativeOpenVINOPerception(camera,runner,ReferenceDifferenceDecoder())
        start = runtime.position
        def plan(evidence):
            return {"action_type":"pick_place", "object_id":"cube-1",
                    "target_bin":"reject" if evidence.anomaly_bbox_xyxy is not None else "accept",
                    "speed_mps":.2, "trajectory":[start,[.03,0.,.07]]}
        orch = PhysicalAIOrchestrator(authority=ReferenceAuthorityEngine(),perception=native,
            vla=LeRobotVLAProvider(plan,model_name="scripted-camera-baseline"),
            actuator=runtime,dispatch_guard=DispatchGuard(scene_hash=camera.scene_hash))
        before = runner.calls
        result = orch.run()
        assert runner.calls == before+1
        assert result.executed and result.dispatch_attempted
        assert result.decision.evidence.metadata["inference_backend"] == "openvino-native"
        assert result.decision.authorized_action.target_bin == ("reject" if marked else "accept")
        assert result.actuator_result["simulation_steps"] > 0
        assert orch.receipts.verify()
        assert result.total_latency_ms >= result.decision.evidence.metadata["native_inference_ms"]
