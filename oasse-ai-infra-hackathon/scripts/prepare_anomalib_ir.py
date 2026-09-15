"""Prepare an exported Anomalib OpenVINO IR for the native perception contract.

An Anomalib OpenVINO export is not directly consumable by ``OpenVINOIRRunner``:
its batch dimension is dynamic and it exposes boolean ``pred_label``/``pred_mask``
tensors alongside the numeric outputs. This utility pins the batch to one and
exposes only ``pred_score`` and ``anomaly_map``.

The transformation is interface-only. Trained weights, embedded preprocessing and
embedded post-processing are carried through untouched; nothing here retrains,
re-thresholds or re-normalizes the model.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

from oasse_physical_ai.providers.openvino_runtime import artifact_digest

MAX_OUTPUT_ELEMENTS = 1_000_000


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _single_name(port) -> str:
    names = sorted(port.get_names())
    if len(names) != 1:
        raise ValueError(f"expected exactly one tensor name, found {names}")
    return names[0]


def _elements(partial_shape) -> int:
    total = 1
    for dimension in partial_shape:
        total *= dimension.get_length()
    return total


def prepare(source: str | Path, target: str | Path, height: int, width: int, *,
            score_name: str = "pred_score", map_name: str = "anomaly_map") -> dict:
    """Emit a static single-batch two-output artifact and describe its provenance."""
    import openvino as ov

    if type(height) is not int or type(width) is not int or height <= 0 or width <= 0:
        raise ValueError("height and width must be positive integers")
    source, target = Path(source), Path(target)
    if source.suffix.lower() != ".xml" or target.suffix.lower() != ".xml":
        raise ValueError("source and target must be OpenVINO IR .xml paths")

    model = ov.Core().read_model(source)
    if len(model.inputs) != 1:
        raise ValueError(f"expected exactly one input, found {len(model.inputs)}")
    port = model.input(0)
    if port.get_element_type() != ov.Type.f32:
        raise ValueError(f"input must be float32, found {port.get_element_type()}")
    shape = port.get_partial_shape()
    if shape.rank.is_dynamic or shape.rank.get_length() != 4:
        raise ValueError("input must be a rank-4 NCHW tensor")
    if shape[1].is_dynamic or shape[1].get_length() != 3:
        raise ValueError("input channel dimension must be exactly 3 (RGB)")
    for axis, expected, label in ((2, height, "height"), (3, width, "width")):
        if shape[axis].is_dynamic or shape[axis].get_length() != expected:
            raise ValueError(
                f"source {label} is {shape[axis]} but {expected} was requested; re-export the "
                "model at the target resolution rather than reshaping it spatially")

    # Only the batch dimension is pinned. Spatial dimensions are never rewritten.
    model.reshape({port: ov.PartialShape([1, 3, height, width])})

    located: dict[str, list] = {score_name: [], map_name: []}
    for output in model.outputs:
        name = _single_name(output)
        if name in located:
            located[name].append(output)
    for wanted, ports in located.items():
        if not ports:
            available = sorted(_single_name(output) for output in model.outputs)
            raise ValueError(f"required output {wanted!r} is not present; available: {available}")
        if len(ports) > 1:
            raise ValueError(f"output name {wanted!r} is ambiguous; refusing to guess")
    score_port, map_port = located[score_name][0], located[map_name][0]

    for label, output in ((score_name, score_port), (map_name, map_port)):
        if output.get_element_type() != ov.Type.f32:
            raise ValueError(f"{label} must be float32, found {output.get_element_type()}")
    if _elements(score_port.get_partial_shape()) != 1:
        raise ValueError(f"{score_name} must be a single scalar per image")
    map_shape = map_port.get_partial_shape()
    if map_shape.rank.get_length() not in (3, 4):
        raise ValueError(f"{map_name} must be spatial with rank 3 or 4")
    if map_shape[-2].get_length() != height or map_shape[-1].get_length() != width:
        raise ValueError(f"{map_name} spatial dimensions do not match {height}x{width}")

    trimmed = ov.Model([score_port, map_port], model.get_parameters(), "oasse_prepared_anomalib")
    target.parent.mkdir(parents=True, exist_ok=True)
    ov.save_model(trimmed, str(target), compress_to_fp16=False)

    emitted = _verify(target, height, width, score_name, map_name)
    weights = target.with_suffix(".bin")
    return {
        "schema": "oasse.prepared_anomalib_ir/v0.1",
        "preparation": {
            "source_xml": str(source),
            "target_xml": str(target),
            "operations": ["reshape_batch_to_1", "restrict_outputs_to_score_and_map"],
            "semantics_changed": False,
            "statement": ("Interface-only transformation. Embedded preprocessing, trained "
                          "weights, thresholds and post-processing are carried through "
                          "unmodified; only batch size and output exposure changed."),
        },
        "hashes": {
            "source_xml_sha256": sha256_file(source),
            "source_bin_sha256": sha256_file(source.with_suffix(".bin")),
            "prepared_xml_sha256": sha256_file(target),
            "prepared_bin_sha256": sha256_file(weights),
            "artifact_digest": artifact_digest(target.read_bytes(), weights.read_bytes()),
        },
        "input": {"shape": [1, 3, height, width], "dtype": "float32",
                  "layout": "NCHW-f32-RGB-div255", "static": True},
        "outputs": emitted,
        "open_items": ["image and pixel thresholds require calibration on held-out task data"],
    }


def _verify(target: Path, height: int, width: int, score_name: str, map_name: str) -> dict:
    """Reload the emitted artifact and confirm it satisfies the runner contract."""
    import openvino as ov

    model = ov.Core().read_model(target)
    if len(model.inputs) != 1:
        raise ValueError("verification failed: emitted artifact does not have one input")
    port = model.input(0)
    shape = port.get_partial_shape()
    if shape.is_dynamic or [d.get_length() for d in shape] != [1, 3, height, width]:
        raise ValueError(f"verification failed: input is not static [1,3,{height},{width}]")
    if port.get_element_type() != ov.Type.f32:
        raise ValueError("verification failed: emitted input is not float32")
    if len(model.outputs) != 2:
        raise ValueError(f"verification failed: expected 2 outputs, found {len(model.outputs)}")
    emitted = {}
    for output in model.outputs:
        name = _single_name(output)
        shape = output.get_partial_shape()
        if shape.is_dynamic:
            raise ValueError(f"verification failed: output {name} is dynamic")
        if output.get_element_type() != ov.Type.f32:
            raise ValueError(f"verification failed: output {name} is not float32")
        count = _elements(shape)
        if not 0 < count <= MAX_OUTPUT_ELEMENTS:
            raise ValueError(f"verification failed: output {name} is not bounded")
        emitted[name] = {"shape": [d.get_length() for d in shape], "elements": count}
    if set(emitted) != {score_name, map_name}:
        raise ValueError(f"verification failed: emitted outputs are {sorted(emitted)}")
    return emitted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="exported Anomalib OpenVINO IR .xml")
    parser.add_argument("--target", required=True, help="prepared IR .xml to write")
    parser.add_argument("--height", required=True, type=int)
    parser.add_argument("--width", required=True, type=int)
    parser.add_argument("--score-name", default="pred_score")
    parser.add_argument("--map-name", default="anomaly_map")
    parser.add_argument("--provenance", help="optional provenance JSON output path")
    args = parser.parse_args()

    record = prepare(args.source, args.target, args.height, args.width,
                     score_name=args.score_name, map_name=args.map_name)
    record["prepared_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    encoded = json.dumps(record, indent=2, allow_nan=False) + "\n"
    if args.provenance:
        path = Path(args.provenance)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
