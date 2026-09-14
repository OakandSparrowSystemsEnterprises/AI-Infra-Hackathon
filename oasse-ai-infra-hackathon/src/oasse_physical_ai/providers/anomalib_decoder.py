"""Explicit decoding contract for exported Anomalib score/map outputs.

This does not train a model or imply its thresholds are calibrated. The IR's
preprocessing must match the RGB runner; record its exact export contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

from ..normalization import number, text
from .openvino_runtime import RGBSpec


@dataclass(frozen=True)
class AnomalibOutputContract:
    image_threshold: float
    pixel_threshold: float
    confidence: float
    calibration_id: str
    score_name: str = "pred_score"
    map_name: str = "anomaly_map"
    model_id: str = "anomalib-export"

    def __post_init__(self) -> None:
        number(self.image_threshold, "image_threshold", minimum=0)
        number(self.pixel_threshold, "pixel_threshold", minimum=0)
        number(self.confidence, "confidence", minimum=0, maximum=1)
        for name in ("calibration_id", "score_name", "map_name", "model_id"):
            text(getattr(self, name), name)


class AnomalibDecoder:
    """Use explicit thresholds. Raw anomaly scores are never called probabilities."""

    def __init__(self, contract: AnomalibOutputContract) -> None:
        if not isinstance(contract, AnomalibOutputContract):
            raise TypeError("expected AnomalibOutputContract")
        self.contract = contract

    def __call__(self, outputs: Mapping[str, Any], spec: RGBSpec) -> dict:
        import numpy as np
        c = self.contract
        score = np.asarray(outputs[c.score_name])
        anomaly = np.asarray(outputs[c.map_name])
        if score.shape not in {(), (1,), (1, 1)} or score.dtype.kind not in "fiu":
            raise ValueError("pred_score must be one numeric value")
        if anomaly.shape not in {(1, 1, spec.height, spec.width), (1, spec.height, spec.width)}:
            raise ValueError("anomaly_map must match the declared image resolution")
        if anomaly.dtype.kind not in "fiu" or not np.isfinite(anomaly).all() or (anomaly < 0).any():
            raise ValueError("anomaly_map must be finite and nonnegative")
        raw_score = number(float(score.reshape(-1)[0]), "pred_score", minimum=0)
        defect = raw_score >= c.image_threshold
        pixels = anomaly.reshape(spec.height, spec.width)
        ys, xs = np.where(pixels >= c.pixel_threshold)
        bbox = None if not len(xs) else [float(xs.min()/spec.width), float(ys.min()/spec.height),
                                       float((xs.max()+1)/spec.width), float((ys.max()+1)/spec.height)]
        if defect and bbox is None:
            raise ValueError("defect score has no localization under the declared thresholds")
        return {"confidence": c.confidence, "anomaly_score": 1.0 if defect else 0.0,
                "anomaly_bbox_xyxy": bbox if defect else None,
                "target_label": "defective_cube" if defect else "normal_cube",
                "metadata": {"detector": "anomalib-export-contract", "model_id": c.model_id,
                             "raw_anomaly_score": raw_score, "image_threshold": c.image_threshold,
                             "pixel_threshold": c.pixel_threshold, "calibration_id": c.calibration_id,
                             "score_encoding": "binary-threshold-not-probability",
                             "confidence_source": "declared-calibration-profile"}}
