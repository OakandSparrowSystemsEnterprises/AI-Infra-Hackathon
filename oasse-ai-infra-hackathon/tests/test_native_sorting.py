import importlib.util
import os
from pathlib import Path

import pytest
pytest.importorskip('mujoco')
pytest.importorskip('openvino')

from oasse_physical_ai.providers.mujoco_sorting import MuJoCoSortingRuntime
from oasse_physical_ai.models import ProposedAction

PATH=Path(__file__).parents[1]/'scripts/run_inspection_demo.py'
spec=importlib.util.spec_from_file_location('inspection_demo',PATH)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


@pytest.mark.skipif(os.environ.get('OASSE_NATIVE_CAMERA_TESTS')!='1',reason='headless GL environment required')
@pytest.mark.parametrize('case',module.CASES)
def test_native_sorting_task(case,tmp_path):
    result,attachments=module.run_case(case,tmp_path/case)
    assert attachments and result['task']['task_complete'] is result['expected_task_complete']
    if case in {'normal_sort','defective_sort','overspeed'}:
        outcome=result['task']['dispatch']['actuator_result']
        assert outcome['before_object_xyz']!=outcome['after_object_xyz']
        assert outcome['events']==['SUCTION_ATTACHED','OBJECT_RELEASED']
        assert outcome['peak_command_speed_mps']<=.35+1e-9
        assert not outcome['physical_grasp_validated']
    if case=='replay':assert result['replay_extra_steps']==0


def test_native_sorter_rejects_trajectory_mismatch_before_effect():
    runtime=MuJoCoSortingRuntime()
    points=runtime.recipe('accept');points[-1][0]=.39
    result=runtime.execute(ProposedAction.pick_place('ev',trajectory=points))
    assert result['status']=='NOT_EXECUTED' and runtime.step_count==0


def test_native_sorter_expired_permission_performs_no_step_or_grip():
    runtime=MuJoCoSortingRuntime()
    result=runtime.execute_guarded(ProposedAction.pick_place('ev',trajectory=runtime.recipe('accept')),lambda:'expired')
    assert result['status']=='NOT_EXECUTED' and runtime.step_count==0 and not runtime.data.eq_active.any()
