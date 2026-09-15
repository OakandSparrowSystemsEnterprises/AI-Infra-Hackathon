"""Contract tests for preparing an Anomalib OpenVINO export for native perception.

Fixtures are authored in-process and are a few kilobytes: no trained weights, no
downloads, no camera and no large artifacts are required.
"""
import argparse
import importlib.util
from pathlib import Path

import pytest
ov = pytest.importorskip("openvino")
import numpy as np
from openvino import opset13 as ops

from oasse_physical_ai.providers.anomalib_decoder import AnomalibDecoder, AnomalibOutputContract
from oasse_physical_ai.providers.openvino_runtime import (
    OpenVINOIRRunner, RGBSpec, artifact_digest,
)

SIZE = 8
SPEC = RGBSpec(SIZE, SIZE)
PIXELS = np.full((SIZE, SIZE, 3), 40, dtype=np.uint8).tobytes()

_path = Path(__file__).parents[1] / "scripts/prepare_anomalib_ir.py"
_spec = importlib.util.spec_from_file_location("prepare_anomalib_ir", _path)
prepare_ir = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prepare_ir)

_live_path = Path(__file__).parents[1] / "scripts/run_live_perception.py"
_live_spec = importlib.util.spec_from_file_location("run_live_perception", _live_path)
live = importlib.util.module_from_spec(_live_spec)
_live_spec.loader.exec_module(live)


def _export(path, *, batch):
    """Reproduce the shape of a real Anomalib export: four outputs, two boolean."""
    image = ops.parameter([batch, 3, SIZE, SIZE], np.float32, name="input")
    anomaly = ops.reduce_mean(image, ops.constant(np.array([1], np.int64)), True)
    score = ops.reduce_max(anomaly, ops.constant(np.array([2, 3], np.int64)), False)
    label = ops.greater(score, ops.constant(np.array([[0.5]], np.float32)))
    mask = ops.greater(anomaly, ops.constant(np.array([[[[0.5]]]], np.float32)))
    model = ov.Model([score, label, anomaly, mask], [image], "anomalib_like")
    for index, name in enumerate(("pred_score", "pred_label", "anomaly_map", "pred_mask")):
        model.output(index).get_tensor().set_names({name})
    ov.serialize(model, str(path), str(path.with_suffix(".bin")))
    return path


@pytest.fixture
def raw_export(tmp_path):
    return _export(tmp_path / "raw.xml", batch=-1)


@pytest.fixture
def prepared(tmp_path, raw_export):
    target = tmp_path / "prepared.xml"
    return target, prepare_ir.prepare(raw_export, target, SIZE, SIZE)


def test_raw_dynamic_export_is_rejected(raw_export):
    with pytest.raises(ValueError, match="static float32 NCHW"):
        OpenVINOIRRunner(raw_export, SPEC, device="CPU")


def test_boolean_outputs_never_reach_the_decoder(tmp_path):
    static_export = _export(tmp_path / "static_four.xml", batch=1)
    runner = OpenVINOIRRunner(static_export, SPEC, device="CPU")
    with pytest.raises(ValueError, match="invalid numeric output"):
        runner.infer(PIXELS)


def test_prepared_artifact_is_accepted(prepared):
    target, record = prepared
    assert record["input"]["shape"] == [1, 3, SIZE, SIZE]
    assert sorted(record["outputs"]) == ["anomaly_map", "pred_score"]
    assert record["preparation"]["semantics_changed"] is False
    outputs = OpenVINOIRRunner(target, SPEC, device="CPU").infer(PIXELS)
    assert sorted(outputs) == ["anomaly_map", "pred_score"]
    assert outputs["anomaly_map"].shape == (1, 1, SIZE, SIZE)


def test_prepared_artifact_digest_pins_bytes(prepared):
    target, record = prepared
    digest = record["hashes"]["artifact_digest"]
    assert digest == artifact_digest(target.read_bytes(), target.with_suffix(".bin").read_bytes())
    OpenVINOIRRunner(target, SPEC, device="CPU", expected_sha256=digest)
    with pytest.raises(ValueError, match="MODEL_ARTIFACT_HASH_MISMATCH"):
        OpenVINOIRRunner(target, SPEC, device="CPU", expected_sha256="0" * 64)


def test_prepared_outputs_decode_through_anomalib_decoder(prepared):
    target, _ = prepared
    outputs = OpenVINOIRRunner(target, SPEC, device="CPU").infer(PIXELS)
    raw = float(np.asarray(outputs["pred_score"]).reshape(-1)[0])
    decoder = AnomalibDecoder(AnomalibOutputContract(
        image_threshold=raw, pixel_threshold=raw, confidence=0.9,
        calibration_id="fixture-calibration", model_id="prepared-fixture"))
    decoded = decoder(outputs, SPEC)
    assert decoded["target_label"] == "defective_cube"
    assert decoded["anomaly_score"] == 1.0
    assert decoded["anomaly_bbox_xyxy"] is not None
    assert decoded["metadata"]["calibration_id"] == "fixture-calibration"


def test_defect_without_localization_fails_closed(prepared):
    """A pixel threshold above the image threshold leaves a defect unlocalized."""
    target, _ = prepared
    outputs = OpenVINOIRRunner(target, SPEC, device="CPU").infer(PIXELS)
    raw = float(np.asarray(outputs["pred_score"]).reshape(-1)[0])
    decoder = AnomalibDecoder(AnomalibOutputContract(
        image_threshold=raw, pixel_threshold=raw + 1.0, confidence=0.9,
        calibration_id="unsafe-threshold-relation", model_id="prepared-fixture"))
    with pytest.raises(ValueError, match="no localization"):
        decoder(outputs, SPEC)


def test_preparation_is_byte_deterministic(tmp_path, raw_export):
    first = prepare_ir.prepare(raw_export, tmp_path / "a.xml", SIZE, SIZE)
    second = prepare_ir.prepare(raw_export, tmp_path / "b.xml", SIZE, SIZE)
    assert first["hashes"]["prepared_xml_sha256"] == second["hashes"]["prepared_xml_sha256"]
    assert first["hashes"]["prepared_bin_sha256"] == second["hashes"]["prepared_bin_sha256"]
    assert first["hashes"]["artifact_digest"] == second["hashes"]["artifact_digest"]


def test_preparation_refuses_mismatched_spatial_dimensions(raw_export, tmp_path):
    with pytest.raises(ValueError, match="re-export"):
        prepare_ir.prepare(raw_export, tmp_path / "wrong.xml", SIZE * 2, SIZE)


def test_preparation_refuses_absent_output_name(raw_export, tmp_path):
    with pytest.raises(ValueError, match="not present"):
        prepare_ir.prepare(raw_export, tmp_path / "missing.xml", SIZE, SIZE,
                           score_name="not_exported")


def _args(**overrides):
    base = dict(camera_index=None, capture_entrypoint=None, context_entrypoint=None,
                camera_id="contract-test-camera")
    base.update(overrides)
    return argparse.Namespace(**base)


@pytest.mark.parametrize("overrides, message", [
    (dict(camera_index=0, capture_entrypoint="pkg:capture"), "not both"),
    (dict(), "supply one ingress"),
    (dict(capture_entrypoint="pkg:capture", context_entrypoint="pkg:context"), "does not apply"),
    (dict(camera_index=0), "--context-entrypoint is required"),
])
def test_ingress_modes_are_mutually_exclusive_and_explicit(overrides, message):
    with pytest.raises(SystemExit, match=message):
        live.build_source(_args(**overrides), SPEC)


def test_sponsor_ingress_needs_no_separate_context():
    source = live.build_source(
        _args(capture_entrypoint="oasse_physical_ai.providers.sponsor_bridge:resolve_callable"),
        SPEC)
    assert source.camera_id == "contract-test-camera"
    assert source.spec is SPEC
