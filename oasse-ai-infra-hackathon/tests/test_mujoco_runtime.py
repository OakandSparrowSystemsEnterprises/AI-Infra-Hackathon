import importlib.util
from pathlib import Path

import pytest
pytest.importorskip("mujoco")

from oasse_physical_ai.models import ProposedAction
from oasse_physical_ai.providers.mujoco_runtime import MuJoCoCartesianRuntime

DEMO = Path(__file__).parents[1] / "scripts/run_mujoco_demo.py"
spec = importlib.util.spec_from_file_location("mujoco_demo", DEMO)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


@pytest.mark.parametrize("case", ["allow", "overspeed", "stale", "future", "occupied", "low_confidence", "scene_changed", "replay"])
def test_native_dynamics_scenario(case):
    result=demo.run_case(case)
    assert result["chain_valid"]
    if result["executed"]:
        outcome=result["outcome"]
        assert outcome["backend"] == "mujoco"
        assert outcome["simulation_steps"] > 0
        assert outcome["simulation_elapsed_s"] > 0
        assert outcome["before_xyz"] != outcome["after_xyz"]
        assert outcome["peak_measured_speed_mps"] <= outcome["speed_mps"] + 1e-6


def command(runtime, **kwargs):
    start=runtime.position
    args={"trajectory":[start,[start[0]+.03,start[1],start[2]+.02]],"speed_mps":.2,**kwargs}
    return ProposedAction.pick_place("ev-test",**args)


def test_native_guard_failure_does_not_step():
    runtime=MuJoCoCartesianRuntime()
    result=runtime.execute_guarded(command(runtime),lambda:"EVIDENCE_EXPIRED_AT_DISPATCH")
    assert result["status"]=="NOT_EXECUTED" and runtime.step_count==0


def test_native_midmotion_expiry_records_partial_unknown():
    runtime=MuJoCoCartesianRuntime()
    result=runtime.execute_guarded(command(runtime),lambda: "EVIDENCE_EXPIRED_AT_DISPATCH" if runtime.step_count>=3 else None)
    assert result["status"]=="UNKNOWN" and runtime.step_count==3
    assert result["partial_effect_possible"] and not runtime.data.ctrl.any()


@pytest.mark.parametrize("points", [[[0,0,0],[10,0,0]],[[0,0,.05],[.03,0,float("nan")]],[[0,0,.05],[0,0,0]]])
def test_native_rejects_invalid_trajectory_before_steps(points):
    runtime=MuJoCoCartesianRuntime()
    result=runtime.execute(command(runtime,trajectory=points))
    assert result["status"]=="NOT_EXECUTED" and runtime.step_count==0


def test_native_step_budget_is_not_reported_as_success():
    runtime=MuJoCoCartesianRuntime(max_steps=1)
    result=runtime.execute(command(runtime))
    assert result["status"]=="UNKNOWN" and runtime.step_count==1
    assert result["partial_effect_possible"]
