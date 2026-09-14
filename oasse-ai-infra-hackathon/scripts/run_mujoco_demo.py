"""Exercise native MuJoCo dynamics and dispatch failures without robot hardware."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json

from oasse_physical_ai.dispatch import DispatchGuard
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine
from oasse_physical_ai.providers.lerobot_mujoco import LeRobotVLAProvider
from oasse_physical_ai.providers.mujoco_runtime import MuJoCoCartesianRuntime, MuJoCoStatePerception


def run_case(case: str) -> dict:
    runtime = MuJoCoCartesianRuntime()
    source = MuJoCoStatePerception(runtime)
    evidence = source.observe()
    if case == "stale":
        evidence = replace(evidence, captured_at_ms=evidence.captured_at_ms - 2000)
    elif case == "future":
        evidence = replace(evidence, captured_at_ms=evidence.captured_at_ms + 5000)
    elif case == "occupied":
        evidence = replace(evidence, workspace_clear=False)
    elif case == "low_confidence":
        evidence = replace(evidence, confidence=0.1)
    elif case == "scene_changed":
        runtime.move_object([0.2, 0.2, 0.025])

    class Fixed:
        def observe(self, scenario="allow"):
            return evidence

    start = runtime.position
    policy = LeRobotVLAProvider(lambda _: {
        "action_type": "pick_place", "object_id": "cube-1", "target_bin": "accept",
        "speed_mps": 0.8 if case == "overspeed" else 0.2,
        "trajectory": [start, [start[0] + 0.03, start[1], start[2] + 0.02]],
    }, model_name="scripted-cartesian-baseline")
    guard = DispatchGuard(scene_hash=runtime.scene_hash)
    orchestrator = PhysicalAIOrchestrator(authority=ReferenceAuthorityEngine(), perception=Fixed(),
                                         vla=policy, actuator=runtime, dispatch_guard=guard)
    first = orchestrator.run()
    if case == "replay":
        before_steps = runtime.step_count
        result = orchestrator.run()
        assert runtime.step_count == before_steps, "replayed evidence advanced physics"
    else:
        result = first
    should_run = case in {"allow", "overspeed"}
    assert result.executed == should_run, result.to_dict()
    assert orchestrator.receipts.verify(), "receipt chain failed"
    if should_run:
        assert result.actuator_result["simulation_steps"] > 0
        assert result.actuator_result["peak_command_speed_mps"] <= 0.35 + 1e-9
    elif case != "replay":
        assert runtime.step_count == 0, "blocked command advanced physics"
    return {"scenario": case, "verdict": result.decision.verdict.value,
            "executed": result.executed, "dispatch_attempted": result.dispatch_attempted,
            "total_physics_steps": runtime.step_count, "chain_valid": True,
            "reasons": result.decision.reason_codes, "outcome": result.actuator_result}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Write a JSON verification record")
    args = parser.parse_args()
    results = [run_case(case) for case in ("allow", "overspeed", "stale", "future", "occupied", "low_confidence", "scene_changed", "replay")]
    payload = {"runtime": "native-mujoco", "perception": "simulator-ground-truth",
               "policy": "scripted-not-trained-vla", "robot": "cartesian-not-so101", "results": results}
    encoded = json.dumps(payload, indent=2, allow_nan=False)
    print(encoded)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(encoded + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
