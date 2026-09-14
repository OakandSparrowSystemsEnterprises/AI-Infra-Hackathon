"""Local dispatch checks. These can remove permission, never grant it."""
from __future__ import annotations

from collections import deque
from dataclasses import asdict
import hashlib
import json
import time
from typing import Callable

from .models import EvidenceFrame, ProposedAction
from .normalization import plain, integer, number, text, trajectory


def fingerprint(value: object) -> str:
    data = plain(asdict(value))
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_inputs(evidence: EvidenceFrame, action: ProposedAction | None = None) -> None:
    integer(evidence.captured_at_ms, "captured_at_ms")
    for name in ("evidence_id", "camera_id", "frame_hash"):
        text(getattr(evidence, name), name)
    number(evidence.confidence, "confidence", minimum=0, maximum=1)
    number(evidence.anomaly_score, "anomaly_score", minimum=0, maximum=1)
    if type(evidence.workspace_clear) is not bool:
        raise TypeError("workspace_clear must be boolean")
    if evidence.frame_sequence is not None:
        integer(evidence.frame_sequence, "frame_sequence")
    fingerprint(evidence)
    if action is not None:
        for name in ("action_id", "actor_id", "evidence_id", "action_type", "object_id", "target_bin"):
            text(getattr(action, name), name)
        integer(action.requested_at_ms, "requested_at_ms")
        number(action.speed_mps, "speed_mps", minimum=0)
        trajectory(action.trajectory)
        fingerprint(action)


class DispatchGuard:
    """Per-orchestrator replay window and launch-time freshness/scene checks.

    Identical pixels in NEW captures are not classified as a replay. Identity
    reuse, non-increasing sequences, and backward capture times are rejected.
    State is in memory; restart/durable anti-replay is outside this demo.
    """

    def __init__(self, max_age_ms: int = 500, *, clock_ms: Callable[[], int] | None = None,
                 scene_hash: Callable[[], str] | None = None, history_size: int = 4096) -> None:
        self.max_age_ms = integer(max_age_ms, "max_age_ms")
        self.clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        self.scene_hash = scene_hash
        if type(history_size) is not int or history_size < 1:
            raise ValueError("history_size must be positive")
        self.history_size = history_size
        self._seen: set[tuple[str, str]] = set()
        self._history: deque[tuple[str, str]] = deque()
        self._cameras: dict[str, tuple[int | None, int]] = {}

    def freshness(self, evidence: EvidenceFrame) -> str | None:
        now = self.clock_ms()
        if evidence.captured_at_ms > now:
            return "EVIDENCE_IN_FUTURE"
        if now - evidence.captured_at_ms > self.max_age_ms:
            return "EVIDENCE_EXPIRED_AT_DISPATCH"
        return None

    def check(self, evidence: EvidenceFrame, action: ProposedAction) -> str | None:
        reason = self.freshness(evidence)
        if reason:
            return reason
        if ("evidence", evidence.evidence_id) in self._seen or ("action", action.action_id) in self._seen:
            return "EVIDENCE_OR_ACTION_REPLAYED"
        previous = self._cameras.get(evidence.camera_id)
        if previous is not None:
            sequence, captured = previous
            if evidence.captured_at_ms < captured:
                return "CAPTURE_TIME_REGRESSED"
            if sequence is not None:
                if evidence.frame_sequence is None or evidence.frame_sequence <= sequence:
                    return "FRAME_SEQUENCE_REUSED"
        if self.scene_hash is not None:
            if not evidence.scene_hash:
                return "SCENE_STATE_UNAVAILABLE"
            if self.scene_hash() != evidence.scene_hash:
                return "SCENE_CHANGED"
        if len(self._cameras) >= 64 and evidence.camera_id not in self._cameras:
            return "CAPTURE_STREAM_CAPACITY"
        return None

    def consume(self, evidence: EvidenceFrame, action: ProposedAction) -> None:
        # Called under the orchestrator's lock, BEFORE the actuator is invoked.
        for key in (("evidence", evidence.evidence_id), ("action", action.action_id)):
            self._seen.add(key)
            self._history.append(key)
        while len(self._history) > self.history_size * 2:
            self._seen.discard(self._history.popleft())
        previous = self._cameras.get(evidence.camera_id)
        sequence = evidence.frame_sequence
        if sequence is None and previous is not None:
            sequence = previous[0]
        self._cameras[evidence.camera_id] = (sequence, evidence.captured_at_ms)
