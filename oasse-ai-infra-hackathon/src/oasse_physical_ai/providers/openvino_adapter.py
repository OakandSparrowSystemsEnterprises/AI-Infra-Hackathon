"""Perception contract adapter. The inference callback supplies the model runtime."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable, Optional, Protocol

from ..models import EvidenceFrame, ProposedAction
from ..normalization import plain as _plain, number as _number, integer, text, vector
from .perception import frame_sha256


@dataclass(frozen=True)
class CapturedFrame:
    data: bytes
    captured_at_ms: int
    camera_id: str = "camera-1"
    sequence: Optional[int] = None


class FrameSource(Protocol):
    def capture(self) -> CapturedFrame: ...


InferenceFn = Callable[[bytes], Mapping[str, Any]]


class OpenVINOPerceptionProvider:
    """Preserve a capture and normalize explicit observations, not permissions."""

    def __init__(self, frame_source: FrameSource, infer: InferenceFn) -> None:
        self.frame_source = frame_source
        self.infer = infer

    def observe(self, scenario: str = "live") -> EvidenceFrame:
        frame = self.frame_source.capture()
        if not isinstance(frame.data, (bytes, bytearray)) or not frame.data:
            raise ValueError("captured frame must contain bytes")
        # Copy before inference so a mutable camera buffer cannot change the hash.
        data = bytes(frame.data)
        captured = integer(_plain(frame.captured_at_ms), "captured_at_ms")
        camera = text(frame.camera_id, "camera_id")
        sequence = None if frame.sequence is None else integer(_plain(frame.sequence), "sequence")
        output = self.infer(data)
        if not isinstance(output, Mapping):
            raise TypeError("inference output must be a mapping")
        raw = _plain(output)
        missing = {"confidence", "workspace_clear", "anomaly_score"} - raw.keys()
        if missing:
            raise ValueError("missing required observations: " + ", ".join(sorted(missing)))
        confidence = _number(raw["confidence"], "confidence", minimum=0.0, maximum=1.0)
        anomaly = _number(raw["anomaly_score"], "anomaly_score", minimum=0.0, maximum=1.0)
        clear = raw["workspace_clear"]
        if type(clear) is not bool:
            raise TypeError("workspace_clear must be an explicit boolean")
        label = text(raw.get("target_label", "cube"), "target_label")
        bbox = None if raw.get("anomaly_bbox_xyxy") is None else vector(raw["anomaly_bbox_xyxy"], "anomaly_bbox_xyxy", 4)
        if bbox is not None and not (0 <= bbox[0] <= bbox[2] <= 1 and 0 <= bbox[1] <= bbox[3] <= 1):
            raise ValueError("bbox must be ordered normalized XYXY coordinates")
        pose = None if raw.get("object_pose_xyzrpy") is None else vector(raw["object_pose_xyzrpy"], "object_pose_xyzrpy", 6)
        dimensions = None if raw.get("object_dimensions_xyz") is None else vector(raw["object_dimensions_xyz"], "object_dimensions_xyz", 3)
        if dimensions is not None and any(size <= 0 for size in dimensions):
            raise ValueError("object dimensions must be positive")
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be an object")
        digest = frame_sha256(data)
        identity = json.dumps([camera, captured, sequence, digest], separators=(",", ":")).encode()
        return EvidenceFrame(
            evidence_id="ev-" + hashlib.sha256(identity).hexdigest(),
            captured_at_ms=captured, confidence=confidence, workspace_clear=clear,
            anomaly_score=anomaly, target_label=label, camera_id=camera, frame_hash=digest,
            anomaly_bbox_xyxy=bbox, object_pose_xyzrpy=pose,
            object_dimensions_xyz=dimensions, frame_sequence=sequence,
            metadata={**metadata, "provider": "openvino", "inference_backend": "injected"},
        )


class OpenVINOPhysicalAIAdapter:
    """Legacy unbound interface retained for compatibility; not a live runtime."""

    def observe(self) -> EvidenceFrame:
        raise NotImplementedError("Use OpenVINOPerceptionProvider with a frame source and model")

    def propose(self, evidence: EvidenceFrame) -> ProposedAction:
        raise NotImplementedError("Use a VLAProvider")

    def execute(self, action: ProposedAction) -> dict:
        raise NotImplementedError("Use an Actuator behind the authority boundary")
