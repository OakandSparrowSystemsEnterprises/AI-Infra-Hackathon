"""These tests use real OpenVINO, never an injected fake native runner."""
from dataclasses import replace
import hashlib
from pathlib import Path

import pytest
ov = pytest.importorskip("openvino")
import numpy as np

from oasse_physical_ai.providers.openvino_runtime import (
    RGBSpec, RGBFrame, OpenVINOIRRunner, NativeOpenVINOPerception,
    ReferenceDifferenceDecoder, export_reference_difference,
)


@pytest.fixture(scope="module")
def model(tmp_path_factory):
    directory = tmp_path_factory.mktemp("native_ir")
    spec = RGBSpec(16, 16)
    reference = np.full((16,16,3), 200, dtype=np.uint8).tobytes()
    path = directory / "reference.xml"
    digest = export_reference_difference(reference, spec, path)
    return path, spec, digest, reference


@pytest.fixture(scope="module")
def runner(model):
    path, spec, digest, _ = model
    return OpenVINOIRRunner(path, spec, expected_sha256=digest)


def test_real_ir_compiles_and_runs_cpu(model, runner):
    output = runner.infer(model[3])
    assert output["anomaly_map"].shape == (1,16,16)
    assert np.max(np.abs(output["anomaly_map"])) < 1e-6
    assert runner.execution_devices == ["CPU"]
    assert runner.model_sha256 == model[2]


def test_pixels_change_native_output_and_localize_defect(model, runner):
    image = np.full((16,16,3), 200, dtype=np.uint8)
    image[4:8,5:9,:] = 0
    output = runner.infer(image.tobytes())
    observation = ReferenceDifferenceDecoder()(output, model[1])
    assert observation["anomaly_score"] == pytest.approx(200/255, abs=1e-6)
    assert observation["anomaly_bbox_xyxy"] == [5/16,4/16,9/16,8/16]


def test_outputs_do_not_alias_request_storage(model, runner):
    first = runner.infer(model[3])
    first["anomaly_map"][:] = 20
    second = runner.infer(model[3])
    assert np.max(second["anomaly_map"]) < 1e-6


def test_hash_mismatch_refuses_model(model):
    with pytest.raises(ValueError, match="HASH_MISMATCH"):
        OpenVINOIRRunner(model[0], model[1], expected_sha256="0"*64)


def test_wrong_tensor_contract_refuses_model(model):
    with pytest.raises(ValueError, match="model input"):
        OpenVINOIRRunner(model[0], RGBSpec(32,32))


@pytest.mark.parametrize("device", ["AUTO", "MULTI:CPU,GPU", "", "HETERO:CPU", None])
def test_no_implicit_device_fallback(model, device):
    with pytest.raises(ValueError): OpenVINOIRRunner(model[0], model[1], device=device)


@pytest.mark.parametrize("data", [b"", b"incorrect", bytearray(16*16*3)])
def test_exact_input_contract(model, runner, data):
    before = runner.calls
    with pytest.raises(ValueError): runner.infer(data)
    assert runner.calls == before


@pytest.mark.parametrize("dimensions", [(0,16),(16,513),(True,16),(16,8.5)])
def test_spec_bounds(dimensions):
    with pytest.raises(ValueError): RGBSpec(*dimensions)


def test_loaded_model_is_bound_to_original_bytes(model, tmp_path):
    path = tmp_path / "copy.xml"
    path.write_bytes(model[0].read_bytes())
    path.with_suffix(".bin").write_bytes(model[0].with_suffix(".bin").read_bytes())
    loaded = OpenVINOIRRunner(path, model[1], expected_sha256=model[2])
    path.with_suffix(".bin").write_bytes(b"corrupted after load")
    assert np.max(loaded.infer(model[3])["anomaly_map"]) < 1e-6
    assert loaded.model_sha256 == model[2]


def test_native_perception_preserves_pixels_and_labels_context(model, runner):
    frame = RGBFrame(model[3], 1700000000000, "test-rgb", 5, width=16,height=16,
                     workspace_clear=True,context_source="declared-test-context",scene_hash="scene")
    class Source:
        def capture(self): return frame
    evidence = NativeOpenVINOPerception(Source(),runner,ReferenceDifferenceDecoder()).observe()
    assert evidence.captured_at_ms == frame.captured_at_ms
    assert evidence.frame_hash == hashlib.sha256(frame.data).hexdigest()
    assert evidence.scene_hash == "scene"
    assert evidence.metadata["inference_backend"] == "openvino-native"
    assert evidence.metadata["context_source"] == "declared-test-context"


def test_missing_workspace_context_never_invents_clear(model, runner):
    class Source:
        def capture(self): return RGBFrame(model[3], 1700000000000, width=16,height=16)
    with pytest.raises(ValueError, match="workspace context"):
        NativeOpenVINOPerception(Source(),runner,ReferenceDifferenceDecoder()).observe()


@pytest.mark.parametrize("output", [{}, {"anomaly_map": np.zeros((2,2))},
    {"anomaly_map": np.full((1,16,16),np.nan)}, {"anomaly_map": np.full((1,16,16),-1)}])
def test_invalid_model_output_is_rejected(model, output):
    with pytest.raises(ValueError): ReferenceDifferenceDecoder()(output, model[1])
