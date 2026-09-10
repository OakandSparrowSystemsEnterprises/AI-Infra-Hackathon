from __future__ import annotations

from dataclasses import replace
import time

from ..models import EvidenceFrame


class MockPerceptionProvider:
    def observe(self, scenario: str = "allow") -> EvidenceFrame:
        now = int(time.time() * 1000)
        base = EvidenceFrame.fresh(
            captured_at_ms=now,
            confidence=0.98,
            workspace_clear=True,
            anomaly_score=0.02,
            target_label="normal_cube",
            frame_hash=f"frame-{scenario}-{now}",
        )
        if scenario == "stale":
            return replace(base, captured_at_ms=now - 2_000)
        if scenario == "occupied":
            return replace(base, workspace_clear=False)
        if scenario == "low_confidence":
            return replace(base, confidence=0.42)
        if scenario == "defect":
            return replace(base, anomaly_score=0.96, target_label="defective_cube")
        return base
