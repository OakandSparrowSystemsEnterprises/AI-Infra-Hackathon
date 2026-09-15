"""Run trained perception against a real camera and emit bounded evidence records.

Wires existing components only:

    OpenCVRGBSource | SponsorRGBSource
        -> OpenVINOIRRunner (hash-pinned prepared artifact)
        -> AnomalibDecoder (calibrated thresholds)
        -> NativeOpenVINOPerception
        -> EvidenceFrame

This script observes. It never proposes, authorizes or actuates, and it never
supplies workspace context of its own: OpenCV ingress requires an explicitly
named context provider, and sponsor ingress requires the sponsor callback to
carry its own explicit context through the sponsor bridge.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from oasse_physical_ai.providers.anomalib_decoder import AnomalibDecoder, AnomalibOutputContract
from oasse_physical_ai.providers.opencv_camera import OpenCVRGBSource
from oasse_physical_ai.providers.openvino_runtime import (
    NativeOpenVINOPerception, OpenVINOIRRunner, RGBSpec, artifact_digest,
)
from oasse_physical_ai.providers.sponsor_bridge import SponsorRGBSource, resolve_callable

# Kept out of evidence records: raw tensors and image arrays never enter metadata.
_PROVENANCE_KEYS = (
    "provider", "inference_backend", "openvino_version", "model_sha256",
    "requested_device", "execution_devices", "native_inference_calls",
    "native_inference_ms", "input_layout", "detector", "model_id",
    "raw_anomaly_score", "image_threshold", "pixel_threshold", "calibration_id",
    "score_encoding", "confidence_source", "context_source", "geometry_source",
    "workspace_source", "image_source",
)


def build_source(args, spec: RGBSpec):
    """Select exactly one camera ingress mode; never blend the two."""
    opencv_mode = args.camera_index is not None
    sponsor_mode = args.capture_entrypoint is not None
    if opencv_mode and sponsor_mode:
        raise SystemExit("choose one ingress: --camera-index or --capture-entrypoint, not both")
    if not opencv_mode and not sponsor_mode:
        raise SystemExit("supply one ingress: --camera-index or --capture-entrypoint")

    if sponsor_mode:
        if args.context_entrypoint is not None:
            raise SystemExit(
                "--context-entrypoint does not apply to sponsor ingress; the sponsor capture "
                "callback must carry its own explicit workspace and timing context")
        return SponsorRGBSource(resolve_callable(args.capture_entrypoint), spec,
                                camera_id=args.camera_id)

    if args.context_entrypoint is None:
        raise SystemExit(
            "--context-entrypoint is required for OpenCV ingress; workspace context must come "
            "from a named source and is never supplied by this script")
    return OpenCVRGBSource(args.camera_index, spec, resolve_callable(args.context_entrypoint),
                           camera_id=args.camera_id)


def evidence_record(evidence) -> dict:
    """Bounded, JSON-safe view of an EvidenceFrame. No pixels, no tensors."""
    metadata = {key: evidence.metadata[key]
                for key in _PROVENANCE_KEYS if key in evidence.metadata}
    return {
        "evidence_id": evidence.evidence_id,
        "frame_hash": evidence.frame_hash,
        "captured_at_ms": evidence.captured_at_ms,
        "frame_sequence": evidence.frame_sequence,
        "camera_id": evidence.camera_id,
        "target_label": evidence.target_label,
        "anomaly_score": evidence.anomaly_score,
        "anomaly_bbox_xyxy": evidence.anomaly_bbox_xyxy,
        "confidence": evidence.confidence,
        "workspace_clear": evidence.workspace_clear,
        "scene_hash": evidence.scene_hash,
        "metadata": metadata,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="prepared IR .xml")
    parser.add_argument("--expected-digest", required=True,
                        help="artifact_digest() of the prepared artifact")
    parser.add_argument("--height", required=True, type=int)
    parser.add_argument("--width", required=True, type=int)
    parser.add_argument("--device", required=True, help="explicit CPU, GPU or NPU device")
    parser.add_argument("--camera-id", required=True)
    parser.add_argument("--camera-index", type=int, help="OpenCV ingress")
    parser.add_argument("--capture-entrypoint", help="sponsor ingress module:callable")
    parser.add_argument("--context-entrypoint",
                        help="OpenCV ingress only: module:callable returning CameraContext")
    parser.add_argument("--image-threshold", required=True, type=float)
    parser.add_argument("--pixel-threshold", required=True, type=float)
    parser.add_argument("--calibration-id", required=True)
    parser.add_argument("--model-id", default="anomalib-prepared-export")
    parser.add_argument("--confidence", type=float, default=0.9)
    parser.add_argument("--frames", type=int, default=1)
    parser.add_argument("--scenario", default="live")
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.pixel_threshold > args.image_threshold:
        raise SystemExit(
            "pixel_threshold must not exceed image_threshold: a defect scoring above the image "
            "threshold would then have no localization and the decoder would refuse it")
    if args.frames < 1:
        raise SystemExit("--frames must be at least 1")

    model = Path(args.model)
    computed = artifact_digest(model.read_bytes(), model.with_suffix(".bin").read_bytes())
    if computed != args.expected_digest:
        raise SystemExit(f"MODEL_ARTIFACT_HASH_MISMATCH: artifact on disk digests to {computed}")

    spec = RGBSpec(width=args.width, height=args.height)
    runner = OpenVINOIRRunner(model, spec, device=args.device,
                              expected_sha256=args.expected_digest)
    decoder = AnomalibDecoder(AnomalibOutputContract(
        image_threshold=args.image_threshold, pixel_threshold=args.pixel_threshold,
        confidence=args.confidence, calibration_id=args.calibration_id,
        model_id=args.model_id))

    source = build_source(args, spec)
    perception = NativeOpenVINOPerception(source, runner, decoder)

    observations, failures = [], []
    try:
        for index in range(args.frames):
            try:
                observations.append(evidence_record(perception.observe(args.scenario)))
            except Exception as error:  # a refused observation is a result, not a crash
                failures.append({"frame": index, "error": type(error).__name__,
                                 "detail": str(error)[:200]})
    finally:
        close = getattr(source, "close", None)
        if callable(close):
            close()

    result = {
        "schema": "oasse.live_perception_record/v0.1",
        "observed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "ingress": "sponsor" if args.capture_entrypoint else "opencv",
        "camera_id": args.camera_id,
        "model": {"prepared_ir": str(model), "artifact_digest": args.expected_digest,
                  "requested_device": args.device,
                  "height": args.height, "width": args.width},
        "decoder": {"image_threshold": args.image_threshold,
                    "pixel_threshold": args.pixel_threshold,
                    "calibration_id": args.calibration_id, "model_id": args.model_id},
        "observations": observations,
        "failures": failures,
        "requested_frames": args.frames,
        "claim_ceiling": ("Evidence produced under the tested camera, object and environment "
                          "conditions. Not a general defect-detection or safety claim."),
    }
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    raise SystemExit(0 if observations and not failures else 1)


if __name__ == "__main__":
    main()
