"""Native OpenVINO + rendered MuJoCo proof, with no claim of learned grasping."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile

import httpx

from oasse_physical_ai.dispatch import DispatchGuard
from oasse_physical_ai.gatekeeper_client import GatekeeperClient
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine
from oasse_physical_ai.providers.lerobot_mujoco import LeRobotVLAProvider
from oasse_physical_ai.providers.mujoco_runtime import MuJoCoCartesianRuntime
from oasse_physical_ai.providers.mujoco_camera import MuJoCoRGBCamera
from oasse_physical_ai.providers.openvino_runtime import (
    RGBSpec, OpenVINOIRRunner, NativeOpenVINOPerception,
    ReferenceDifferenceDecoder, export_reference_difference,
)

CASES = ("allow", "defect", "overspeed", "stale", "future", "occupied", "low_confidence", "scene_changed", "replay", "authority_outage")


def run_case(case: str, directory: Path) -> dict:
    if case not in CASES:
        raise ValueError("unknown vision scenario")
    directory.mkdir(parents=True, exist_ok=True)
    runtime = MuJoCoCartesianRuntime()
    spec = RGBSpec()
    with MuJoCoRGBCamera(runtime, spec) as camera:
        reference = camera.capture()
        model_path = directory / "reference_difference.xml"
        expected = export_reference_difference(reference.data, spec, model_path)
        runner = OpenVINOIRRunner(model_path, spec, expected_sha256=expected)
        runner.infer(reference.data)  # Compile/runtime warm-up is not an observation.
        camera.marked = case == "defect"
        runtime.workspace_clear = case != "occupied"
        frame = camera.capture()
        class FixedCapture:
            def capture(self): return frame
        perception = NativeOpenVINOPerception(FixedCapture(), runner,
            ReferenceDifferenceDecoder(confidence=.1 if case == "low_confidence" else .99))
        evidence = perception.observe()
        assert evidence.frame_hash == hashlib.sha256(frame.data).hexdigest()
        assert evidence.metadata["inference_backend"] == "openvino-native"
        assert runner.calls == 2
        if case == "defect":
            assert evidence.anomaly_score > .10 and evidence.anomaly_bbox_xyxy is not None
            assert frame.data != reference.data
        else:
            assert evidence.anomaly_score < .00001, evidence.anomaly_score
        if case == "stale":
            evidence = replace(evidence, captured_at_ms=evidence.captured_at_ms - 2000)
        elif case == "future":
            evidence = replace(evidence, captured_at_ms=evidence.captured_at_ms + 5000)
        elif case == "scene_changed":
            camera.marked = True
        class FixedEvidence:
            def observe(self, scenario="allow"): return evidence
        start = runtime.position
        def propose(ev):
            reject = ev.anomaly_bbox_xyxy is not None
            return {"action_type": "pick_place", "object_id": "cube-1",
                    "target_bin": "reject" if reject else "accept",
                    "speed_mps": .8 if case == "overspeed" else .2,
                    "trajectory": [start, [start[0]+.03, start[1]+(-.005 if reject else .005), start[2]+.02]]}
        authority = ReferenceAuthorityEngine()
        if case == "authority_outage":
            def down(request): raise httpx.ConnectError("offline test service", request=request)
            authority = GatekeeperClient("https://gatekeeper.test", transport=httpx.MockTransport(down))
        orch = PhysicalAIOrchestrator(authority=authority, perception=FixedEvidence(),
            vla=LeRobotVLAProvider(propose, model_name="scripted-vision-baseline-not-trained-vla"),
            actuator=runtime, dispatch_guard=DispatchGuard(scene_hash=camera.scene_hash))
        result = orch.run()
        if case == "replay":
            assert result.executed
            previous_steps = runtime.step_count
            result = orch.run()
            assert runtime.step_count == previous_steps
        expected_execution = case in {"allow", "defect", "overspeed"}
        assert result.executed is expected_execution, result.to_dict()
        if expected_execution:
            assert result.actuator_result["simulation_steps"] > 0
            assert result.actuator_result["peak_command_speed_mps"] <= .35 + 1e-9
        elif case != "replay":
            assert runtime.step_count == 0
        if case == "defect":
            assert result.decision.authorized_action.target_bin == "reject"
        assert orch.receipts.verify()
        # Save exact rendered pixels in a portable format, not generated artwork.
        (directory / "observed.ppm").write_bytes(f"P6\n{spec.width} {spec.height}\n255\n".encode()+frame.data)
        return {"scenario": case, "verdict": result.decision.verdict.value,
                "executed": result.executed, "dispatch_attempted": result.dispatch_attempted,
                "reasons": result.decision.reason_codes, "pixel_sha256": evidence.frame_hash,
                "anomaly_score": evidence.anomaly_score, "anomaly_bbox_xyxy": evidence.anomaly_bbox_xyxy,
                "model": runner.provenance(), "physics_steps": runtime.step_count,
                "outcome": result.actuator_result, "receipt_chain_valid": True,
                "receipts": [r.to_dict() for r in orch.receipts.all()]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="JSON verification record")
    parser.add_argument("--artifacts-dir", help="Directory for IR and captured pixel evidence")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="oasse-native-vision-") as temporary:
        directory = Path(args.artifacts_dir or temporary)
        results = [run_case(case, directory / case) for case in CASES]
        payload = {"phase": 3, "inference": "native-openvino-cpu", "images": "native-mujoco-rendered-rgb",
                   "detector": "authored-reference-difference-graph-not-trained",
                   "nonvisual_context": "simulator-ground-truth", "policy": "scripted-not-trained-vla",
                   "robot": "cartesian-harness-not-so101", "grasping_tested": False,
                   "cases_passed": len(results), "results": results}
        encoded = json.dumps(payload, indent=2, allow_nan=False)
        print(encoded)
        if args.output:
            Path(args.output).write_text(encoded+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
