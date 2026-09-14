from __future__ import annotations

"""Intel/OpenVINO perception seam.

This module intentionally keeps OpenVINO itself optional. The on-site integration
supplies a frame source and an inference callable; this adapter owns evidence
normalization, content hashing, and the contract handed to Gatekeeper.
"""

from dataclasses import dataclass
import math
from typing import Any, Callable, Dict, Mapping, Optional, Protocol

from ..models import EvidenceFrame, ProposedAction
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


def _plain(value: Any) -> Any:
    """Convert common framework scalars/arrays to JSON-safe Python values."""
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("non-finite numeric inference output")
        return value
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("inference mapping keys must be strings")
        return {key: _plain(item) for key, item in value.items()}
    if hasattr(value, "item"):
        return _plain(value.item())
    if hasattr(value, "tolist"):
        return _plain(value.tolist())
    raise TypeError(f"unsupported inference value: {type(value).__name__}")


def _number(value: Any, name: str, *, minimum: Optional[float] = None, maximum: Optional[float] = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and number < minimum:
        raise ValueError(f"{name} below minimum")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name} above maximum")
    return number


def _vector(value: Any, name: str, size: int) -> Optional[list[float]]:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != size:
        raise TypeError(f"{name} must contain {size} numeric values")
    return [_number(item, name) for item in value]


class OpenVINOPerceptionProvider:
    """Normalize live camera + OpenVINO output into an EvidenceFrame."""

    def __init__(self, frame_source: FrameSource, infer: InferenceFn) -> None:
        self.frame_source = frame_source
        self.infer = infer

    def observe(self, scenario: str = "live") -> EvidenceFrame:
        frame = self.frame_source.capture()
        if not isinstance(frame.data, (bytes, bytearray)) or not frame.data:
            raise ValueError("captured frame must contain bytes")
        raw = _plain(dict(self.infer(bytes(frame.data))))
        if not isinstance(raw, dict):
            raise TypeError("inference result must be a mapping")

        confidence = _number(raw.get("confidence"), "confidence", minimum=0.0, maximum=1.0)
        anomaly_score = _number(raw.get("anomaly_score", 0.0), "anomaly_score", minimum=0.0, maximum=1.0)
        workspace_clear = raw.get("workspace_clear", True)
        if not isinstance(workspace_clear, bool):
            raise TypeError("workspace_clear must be boolean")
        target_label = raw.get("target_label", "cube")
        if not isinstance(target_label, str) or not target_label.strip():
            raise TypeError("target_label must be a non-empty string")

        bbox = _vector(raw.get("anomaly_bbox_xyxy"), "anomaly_bbox_xyxy", 4)
        pose = _vector(raw.get("object_pose_xyzrpy"), "object_pose_xyzrpy", 6)
        dimensions = _vector(raw.get("object_dimensions_xyz"), "object_dimensions_xyz", 3)
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be an object")

        digest = frame_sha256(bytes(frame.data))
        return EvidenceFrame(
            evidence_id=f"ev-{digest[:12]}-{frame.captured_at_ms}",
            captured_at_ms=int(frame.captured_at_ms),
            confidence=confidence,
            workspace_clear=workspace_clear,
            anomaly_score=anomaly_score,
            target_label=target_label,
            camera_id=frame.camera_id,
            frame_hash=digest,
            anomaly_bbox_xyxy=bbox,
            object_pose_xyzrpy=pose,
            object_dimensions_xyz=dimensions,
            frame_sequence=frame.sequence,
            metadata={"provider": "openvino", **metadata},
        )


class OpenVINOPhysicalAIAdapter:
    """Legacy combined seam retained for compatibility with early skeleton docs."""

    def observe(self) -> EvidenceFrame:
        raise NotImplementedError("Use OpenVINOPerceptionProvider with the event camera pipeline")

    def propose(self, evidence: EvidenceFrame) -> ProposedAction:
        raise NotImplementedError("Use a VLAProvider such as LeRobotVLAProvider")

    def execute(self, action: ProposedAction) -> dict:
        raise NotImplementedError("Use an Actuator implementation behind the authority boundary")
