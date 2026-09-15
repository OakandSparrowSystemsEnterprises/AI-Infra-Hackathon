"""Validated snapshots and local dispatch checks. These never grant permission."""
from __future__ import annotations

from collections import deque
from dataclasses import fields, replace
import hashlib
import json
import threading
import time
from typing import Callable

from .models import AuthorityDecision, EvidenceFrame, ProposedAction, Verdict
from .normalization import plain, integer, number, text, trajectory, vector


def snapshot_fields(value: EvidenceFrame | ProposedAction) -> dict:
    # Avoid unbounded dataclasses.asdict recursion before the normalization budget.
    return plain({field.name: getattr(value, field.name) for field in fields(value)})


def fingerprint(value: EvidenceFrame | ProposedAction) -> str:
    """Portable content fingerprint used for evidence/export boundaries, not hot-path equality."""
    encoded = json.dumps(snapshot_fields(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _validate_joint_action(value: dict[str, float] | None) -> None:
    if value is None:
        return
    if not isinstance(value, dict) or not 1 <= len(value) <= 64:
        raise TypeError("joint_action must be a non-empty bounded object")
    for name, position in value.items():
        text(name, "joint_action key")
        number(position, f"joint_action[{name}]")


def validate_inputs(evidence: EvidenceFrame, action: ProposedAction | None = None) -> None:
    if not isinstance(evidence, EvidenceFrame):
        raise TypeError("expected EvidenceFrame")
    integer(evidence.captured_at_ms, "captured_at_ms")
    for name in ("evidence_id", "camera_id", "frame_hash", "target_label"):
        text(getattr(evidence, name), name)
    number(evidence.confidence, "confidence", minimum=0, maximum=1)
    number(evidence.anomaly_score, "anomaly_score", minimum=0, maximum=1)
    if type(evidence.workspace_clear) is not bool:
        raise TypeError("workspace_clear must be boolean")
    if evidence.frame_sequence is not None:
        integer(evidence.frame_sequence, "frame_sequence")
    if evidence.scene_hash is not None:
        text(evidence.scene_hash, "scene_hash")
    if not isinstance(evidence.metadata, dict):
        raise TypeError("evidence metadata must be an object")
    if evidence.anomaly_bbox_xyxy is not None:
        box = vector(evidence.anomaly_bbox_xyxy, "anomaly_bbox_xyxy", 4)
        if not (0 <= box[0] <= box[2] <= 1 and 0 <= box[1] <= box[3] <= 1):
            raise ValueError("bbox must be ordered normalized XYXY coordinates")
    if evidence.object_pose_xyzrpy is not None:
        vector(evidence.object_pose_xyzrpy, "object_pose_xyzrpy", 6)
    if evidence.object_dimensions_xyz is not None:
        sizes = vector(evidence.object_dimensions_xyz, "object_dimensions_xyz", 3)
        if any(size <= 0 for size in sizes):
            raise ValueError("dimensions must be positive")
    snapshot_fields(evidence)
    if action is not None:
        if not isinstance(action, ProposedAction):
            raise TypeError("expected ProposedAction")
        for name in ("action_id", "actor_id", "evidence_id", "action_type", "object_id", "target_bin"):
            text(getattr(action, name), name)
        integer(action.requested_at_ms, "requested_at_ms")
        number(action.speed_mps, "speed_mps", minimum=0)
        trajectory(action.trajectory)
        _validate_joint_action(action.joint_action)
        if not isinstance(action.metadata, dict):
            raise TypeError("action metadata must be an object")
        snapshot_fields(action)


def copy_evidence(evidence: EvidenceFrame) -> EvidenceFrame:
    return EvidenceFrame(**snapshot_fields(evidence))


def copy_action(action: ProposedAction) -> ProposedAction:
    return ProposedAction(**snapshot_fields(action))


def copy_decision(decision: AuthorityDecision) -> AuthorityDecision:
    if not isinstance(decision, AuthorityDecision) or not isinstance(decision.verdict, Verdict):
        raise TypeError("invalid authority decision")
    text(decision.decision_id, "decision_id")
    text(decision.policy_version, "policy_version")
    integer(decision.evaluated_at_ms, "evaluated_at_ms")
    number(decision.authority_latency_ms, "authority_latency_ms", minimum=0)
    if not isinstance(decision.reason_codes, list):
        raise TypeError("reason_codes must be a list")
    for code in decision.reason_codes:
        text(code, "reason_code")
    validate_inputs(decision.evidence, decision.original_action)
    if decision.authorized_action is not None:
        validate_inputs(decision.evidence, decision.authorized_action)
    return replace(decision, evidence=copy_evidence(decision.evidence),
                   original_action=copy_action(decision.original_action),
                   authorized_action=None if decision.authorized_action is None else copy_action(decision.authorized_action),
                   reason_codes=list(decision.reason_codes))


class DispatchGuard:
    """Bounded replay state, wall-clock checks and monotonic execution leases.

    New captures of identical pixels are permitted. State is in memory and
    does not authenticate sources or survive restarts. reserve() is atomic
    even when a guard is shared by several in-process orchestrators.
    """

    def __init__(self, max_age_ms: int = 500, *, clock_ms: Callable[[], int] | None = None,
                 scene_hash: Callable[[], str] | None = None, history_size: int = 4096,
                 monotonic_ns: Callable[[], int] | None = None) -> None:
        self.max_age_ms = integer(max_age_ms, "max_age_ms")
        self.clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        self.monotonic_ns = monotonic_ns or time.monotonic_ns
        self.scene_hash = scene_hash
        if type(history_size) is not int or not 1 <= history_size <= 100000:
            raise ValueError("history_size must be in [1, 100000]")
        self.history_size = history_size
        self._seen: set[tuple[str, str]] = set()
        self._history: deque[tuple[str, str]] = deque()
        self._cameras: dict[str, tuple[int | None, int]] = {}
        self._lock = threading.RLock()

    def deadline(self, evidence: EvidenceFrame) -> int:
        age = self.clock_ms() - evidence.captured_at_ms
        return self.monotonic_ns() + (self.max_age_ms - max(0, age)) * 1000000

    def freshness(self, evidence: EvidenceFrame, deadline_ns: int | None = None) -> str | None:
        now = self.clock_ms()
        if evidence.captured_at_ms > now:
            return "EVIDENCE_IN_FUTURE"
        if now - evidence.captured_at_ms > self.max_age_ms:
            return "EVIDENCE_EXPIRED_AT_DISPATCH"
        if deadline_ns is not None and self.monotonic_ns() > deadline_ns:
            return "EVIDENCE_LEASE_EXPIRED"
        return None

    def check(self, evidence: EvidenceFrame, action: ProposedAction,
              deadline_ns: int | None = None) -> str | None:
        with self._lock:
            return self._check(evidence, action, deadline_ns)

    def _check(self, evidence: EvidenceFrame, action: ProposedAction,
               deadline_ns: int | None = None) -> str | None:
        reason = self.freshness(evidence, deadline_ns)
        if reason:
            return reason
        if ("evidence", evidence.evidence_id) in self._seen or ("action", action.action_id) in self._seen:
            return "EVIDENCE_OR_ACTION_REPLAYED"
        previous = self._cameras.get(evidence.camera_id)
        if previous is not None:
            sequence, captured = previous
            if evidence.captured_at_ms < captured:
                return "CAPTURE_TIME_REGRESSED"
            if sequence is not None and (evidence.frame_sequence is None or evidence.frame_sequence <= sequence):
                return "FRAME_SEQUENCE_REUSED"
        if self.scene_hash is not None:
            if not evidence.scene_hash:
                return "SCENE_STATE_UNAVAILABLE"
            if self.scene_hash() != evidence.scene_hash:
                return "SCENE_CHANGED"
        if len(self._cameras) >= 64 and evidence.camera_id not in self._cameras:
            return "CAPTURE_STREAM_CAPACITY"
        return None

    def reserve(self, evidence: EvidenceFrame, action: ProposedAction, deadline_ns: int | None = None) -> str | None:
        with self._lock:
            reason = self._check(evidence, action, deadline_ns)
            if reason is None:
                self._consume(evidence, action)
            return reason

    def consume(self, evidence: EvidenceFrame, action: ProposedAction) -> None:
        """Compatibility method. Prefer atomic reserve() at dispatch."""
        with self._lock:
            self._consume(evidence, action)

    def _consume(self, evidence: EvidenceFrame, action: ProposedAction) -> None:
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
