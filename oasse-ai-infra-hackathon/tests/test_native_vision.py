"""Full rendered-camera, native-inference and native-physics smoke tests."""
import importlib.util
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
pytest.importorskip("mujoco")
pytest.importorskip("openvino")
if os.environ.get("OASSE_NATIVE_CAMERA_TESTS") != "1":
    pytest.skip("native renderer suite runs in its declared headless CI job", allow_module_level=True)

from oasse_physical_ai.providers.mujoco_runtime import MuJoCoCartesianRuntime
from oasse_physical_ai.providers.mujoco_camera import MuJoCoRGBCamera

path = Path(__file__).parents[1] / "scripts/run_native_vision_demo.py"
spec = importlib.util.spec_from_file_location("native_vision_demo", path)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


@pytest.mark.parametrize("case", demo.CASES)
def test_native_camera_to_authority_to_physics(case, tmp_path):
    result = demo.run_case(case, tmp_path / case)
    assert result["receipt_chain_valid"]
    assert result["model"]["execution_devices"] == ["CPU"]
    assert result["model"]["native_inference_calls"] == 2
    assert result["model"]["model_sha256"]


def test_identical_pixels_are_new_captures_and_mark_changes_pixels():
    with MuJoCoRGBCamera(MuJoCoCartesianRuntime()) as camera:
        first, second = camera.capture(), camera.capture()
        assert first.data == second.data
        assert second.sequence > first.sequence
        camera.marked = True
        marked = camera.capture()
        assert marked.data != first.data and marked.scene_hash != first.scene_hash


def test_gl_context_rejects_wrong_thread_and_close_is_idempotent():
    camera = MuJoCoRGBCamera(MuJoCoCartesianRuntime())
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with pytest.raises(RuntimeError, match="owner thread"):
                pool.submit(camera.capture).result()
    finally:
        camera.close()
    camera.close()
    with pytest.raises(RuntimeError, match="closed"): camera.capture()
