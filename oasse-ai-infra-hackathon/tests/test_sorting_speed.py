import pytest
pytest.importorskip('mujoco')

from oasse_physical_ai.models import ProposedAction
from oasse_physical_ai.providers.mujoco_sorting import MuJoCoSortingRuntime


@pytest.mark.parametrize('speed',[.2,.35])
@pytest.mark.parametrize('destination',['accept','reject'])
def test_native_sorting_measured_velocity_stays_within_authorized_ceiling(speed,destination):
    runtime=MuJoCoSortingRuntime()
    action=ProposedAction.pick_place('ev',trajectory=runtime.recipe(destination),speed_mps=speed,target_bin=destination)
    result=runtime.execute_guarded(action,lambda:None)
    assert result['status']=='EXECUTED',result
    assert result['peak_command_speed_mps']<=speed*.85+1e-9
    assert result['peak_measured_speed_mps']<=speed+1e-9
    observation=runtime.verify(action)
    assert observation['observed_bin']==destination and observation['object_released']
    assert observation['object_speed_mps']<=.01


def test_native_measured_velocity_violation_is_not_success(monkeypatch):
    runtime=MuJoCoSortingRuntime()
    native_step=runtime.mj.mj_step
    def disturbed(model,data):
        native_step(model,data)
        data.qvel[0]=1.0
    monkeypatch.setattr(runtime.mj,'mj_step',disturbed)
    result=runtime.execute(ProposedAction.pick_place('ev',trajectory=runtime.recipe('accept'),speed_mps=.2))
    assert result['status']=='UNKNOWN' and result['reason']=='MEASURED_SPEED_EXCEEDED'
    assert result['simulation_steps']==1 and result['partial_effect_possible']
    assert result['peak_measured_speed_mps']>=1.0 and not runtime.data.ctrl.any()
