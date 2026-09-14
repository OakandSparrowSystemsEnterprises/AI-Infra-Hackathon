"""Native image inspection followed by actual free-cube transport and verification."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import httpx

from oasse_physical_ai.dispatch import DispatchGuard
from oasse_physical_ai.evidence_bundle import rgb_png, write_bundle, zip_bundle
from oasse_physical_ai.gatekeeper_client import GatekeeperClient
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine
from oasse_physical_ai.providers.lerobot_mujoco import LeRobotVLAProvider
from oasse_physical_ai.providers.mujoco_camera import MuJoCoRGBCamera
from oasse_physical_ai.providers.mujoco_sorting import MuJoCoSortingRuntime
from oasse_physical_ai.providers.openvino_runtime import (
    RGBSpec, OpenVINOIRRunner, NativeOpenVINOPerception, ReferenceDifferenceDecoder, export_reference_difference,
)
from oasse_physical_ai.tasks import InspectionTask

CASES = ("normal_sort", "defective_sort", "overspeed", "stale", "future", "occupied",
         "scene_changed", "authority_outage", "replay", "midmotion_expiry", "obstruction", "postcondition_failure")


def run_case(case: str, directory: Path) -> tuple[dict, dict[str, bytes]]:
    if case not in CASES: raise ValueError("unknown inspection scenario")
    directory.mkdir(parents=True, exist_ok=True)
    runtime = MuJoCoSortingRuntime()
    spec = RGBSpec()
    clock = [0]
    with MuJoCoRGBCamera(runtime, spec) as camera:
        reference = camera.capture()
        path = directory/"reference_difference.xml"
        digest = export_reference_difference(reference.data, spec, path)
        model = OpenVINOIRRunner(path, spec, expected_sha256=digest)
        model.infer(reference.data)
        camera.marked = case == "defective_sort"
        runtime.workspace_clear = case != "occupied"
        frame = camera.capture()
        if case == "stale": frame = replace(frame, captured_at_ms=frame.captured_at_ms-60000)
        if case == "future": frame = replace(frame, captured_at_ms=frame.captured_at_ms+60000)
        if case == "scene_changed": runtime.move_object([.19,.13,.025])
        class FixedCapture:
            def capture(self): return frame
        perception = NativeOpenVINOPerception(FixedCapture(), model, ReferenceDifferenceDecoder())
        def policy(evidence):
            target = "reject" if evidence.anomaly_bbox_xyxy is not None else "accept"
            return {"action_type":"pick_place","object_id":"cube-1","target_bin":target,
                    "speed_mps":.8 if case=="overspeed" else .2,"trajectory":runtime.recipe(target)}
        authority = ReferenceAuthorityEngine()
        if case == "authority_outage":
            def down(request): raise httpx.ConnectError("fixture outage",request=request)
            authority = GatekeeperClient("https://gatekeeper.test", transport=httpx.MockTransport(down))
        guard = DispatchGuard(scene_hash=camera.scene_hash,
                              monotonic_ns=(lambda:clock[0]) if case=="midmotion_expiry" else None)
        if case == "midmotion_expiry":
            def expire(stage):
                if stage=="waypoint_4": clock[0]=600000000
            runtime.stage_callback=expire
        elif case == "obstruction":
            def obstruct(stage):
                if stage=="waypoint_4": runtime.workspace_clear=False
            runtime.stage_callback=obstruct
        orchestrator = PhysicalAIOrchestrator(authority=authority,perception=perception,
            vla=LeRobotVLAProvider(policy,model_name="scripted-sorting-recipe-not-trained-vla"),
            actuator=runtime,dispatch_guard=guard)
        verifier = runtime.verify
        if case == "postcondition_failure":
            def failed_verifier(action):
                return {**runtime.verify(action),"object_released":False,
                        "observation_source":"injected-postcondition-fault"}
            verifier=failed_verifier
        task=InspectionTask(orchestrator,verifier)
        result=task.run()
        before_replay=runtime.step_count
        if case == "replay":
            assert result["task_complete"], result
            result=InspectionTask(orchestrator,verifier).run()
            assert runtime.step_count==before_replay
        expected=case in {"normal_sort","defective_sort","overspeed"}
        assert result["task_complete"] is expected, result
        if expected:
            assert result["dispatch"]["actuator_result"]["simulation_steps"]>0
            assert result["dispatch"]["actuator_result"]["peak_command_speed_mps"]<=.35+1e-9
            observed=result["verification"]["observation"]
            assert observed["observed_bin"]==("reject" if case=="defective_sort" else "accept"), observed
            assert observed["object_released"] and observed["object_speed_mps"]<=.01
        elif case in {"stale","future","occupied","scene_changed","authority_outage"}:
            assert runtime.step_count==0
        elif case in {"midmotion_expiry","obstruction"}:
            assert result["status"]=="UNKNOWN" and runtime.step_count>0
        assert orchestrator.receipts.verify()
        # A second call to the same task is an idempotent read, not a second motion.
        if case != "replay":
            steps=runtime.step_count
            assert task.run()==result and runtime.step_count==steps
        camera.camera.lookat[:]=[.23,0.,.04]
        camera.camera.distance=.65
        runtime.mj.mj_forward(runtime.model,runtime.data)
        final=camera.capture()
        before_name=f"captures/{case}/inspection.png"
        after_name=f"captures/{case}/outcome.png"
        attachments={before_name:rgb_png(frame.data,spec.width,spec.height),
                     after_name:rgb_png(final.data,spec.width,spec.height),
                     f"models/{case}/reference.xml":path.read_bytes(),
                     f"models/{case}/reference.bin":path.with_suffix('.bin').read_bytes()}
        return {"scenario":case,"expected_task_complete":expected,"task":result,
                "physics_steps":runtime.step_count,"replay_extra_steps":runtime.step_count-before_replay if case=="replay" else None,
                "before_image":before_name,"after_image":after_name,
                "inspection_pixel_sha256":hashlib.sha256(frame.data).hexdigest(),"model":model.provenance(),
                "receipts":[r.to_dict() for r in orchestrator.receipts.all()]}, attachments


def rehearse(directory: Path, *, source_commit: str | None = None) -> tuple[dict,dict[str,bytes]]:
    results=[]; attachments={}
    with tempfile.TemporaryDirectory(prefix="oasse-inspection-") as temporary:
        for case in CASES:
            result, files=run_case(case,Path(temporary)/case)
            results.append(result); attachments.update(files)
    return {"schema":"oasse.inspection-rehearsal.v1","source_commit":source_commit,
        "scope":{"inference":"native-openvino","physics":"native-mujoco","grip":"idealized-suction-weld",
                 "detector":"reference-image-difference-not-trained","planner":"scripted-not-trained-vla",
                 "hardware_tested":False,"gatekeeper":"reference-plus-mocked-outage","onsite_submission":False},
        "cases":results},attachments


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--bundle",required=True)
    parser.add_argument("--zip")
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    record,attachments=rehearse(Path(args.bundle),source_commit=commit)
    digest=write_bundle(Path(args.bundle),record,attachments)
    if args.zip: zip_bundle(Path(args.bundle),Path(args.zip))
    print(f"Inspection rehearsal passed: {len(record['cases'])} scenarios; manifest SHA-256 {digest}")


if __name__=="__main__": main()
