from __future__ import annotations

from dataclasses import replace
import hashlib
import time
from typing import Protocol

from ..models import EvidenceFrame


class PerceptionProvider(Protocol):
    def observe(self, scenario: str = "allow") -> EvidenceFrame: ...


def frame_sha256(frame_bytes: bytes) -> str:
    return hashlib.sha256(frame_bytes).hexdigest()


class MockPerceptionProvider:
    def observe(self, scenario: str = "allow") -> EvidenceFrame:
        now = int(time.time() * 1000)
        synthetic_frame = f"mock-frame:{scenario}:{now}".encode("utf-8")
        base = EvidenceFrame.fresh(
            captured_at_ms=now,
            confidence=0.98,
            workspace_clear=True,
            anomaly_score=0.02,
            target_label="normal_cube",
            frame_hash=frame_sha256(synthetic_frame),
            anomaly_bbox_xyxy=None,
            object_pose_xyzrpy=[0.20, 0.00, 0.03, 0.0, 0.0, 0.0],
            object_dimensions_xyz=[0.04, 0.04, 0.04],
            frame_sequence=1,
            metadata={"provider": "mock-perception"},
        )
        if scenario == "stale":
            return replace(base, captured_at_ms=now - 2_000)
        if scenario == "occupied":
            return replace(base, workspace_clear=False)
        if scenario == "low_confidence":
            return replace(base, confidence=0.42)
        if scenario == "defect":
            return replace(
                base,
                anomaly_score=0.96,
                target_label="defective_cube",
                anomaly_bbox_xyxy=[0.35, 0.30, 0.62, 0.58],
            )
        return base
