import time
from unittest.mock import patch

import numpy as np

from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.providers.actuator import SimulatedActuator
from oasse_physical_ai.providers.opencv_camera import CameraContext, OpenCVRGBSource
from oasse_physical_ai.providers.openvino_runtime import RGBSpec
from oasse_physical_ai.tasks import InspectionTask


def test_recursive_task_callback_fails_without_deadlock_or_redispatch():
    class Count(SimulatedActuator):
        calls=0
        def execute(self,action):
            self.calls+=1
            return super().execute(action)
    actuator=Count()
    task=InspectionTask(PhysicalAIOrchestrator(actuator=actuator),lambda _:task.run())
    result=task.run()
    assert result['status']=='UNKNOWN' and actuator.calls==1
    assert task.run()==result


def test_context_sampled_during_acquisition_is_not_future_dated():
    class Capture:
        def isOpened(self): return True
        def set(self,*args): return True
        def read(self): return True,np.zeros((8,8,3),dtype=np.uint8)
        def release(self): pass
    with OpenCVRGBSource(0,RGBSpec(8,8),lambda:CameraContext(1005,True,'sensor'),
        camera_id='test-camera',capture_factory=lambda _:Capture()) as camera:
        with patch('oasse_physical_ai.providers.opencv_camera.time.time',side_effect=[1.0,1.010,1.011]):
            frame=camera.capture()
    assert frame.captured_at_ms==1000
