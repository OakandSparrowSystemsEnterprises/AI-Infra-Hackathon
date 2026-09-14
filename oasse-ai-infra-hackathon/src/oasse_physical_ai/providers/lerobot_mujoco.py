"""Independent policy and simulator callbacks; no tutorial code is vendored."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable

from ..models import EvidenceFrame, ProposedAction
from ..normalization import plain, number, text, trajectory

PolicyFn = Callable[[EvidenceFrame], Mapping[str, Any]]
ExecuteFn = Callable[[ProposedAction], Mapping[str, Any]]


class LeRobotVLAProvider:
    """Normalize an explicit policy proposal. No missing motion is invented."""

    def __init__(self, policy: PolicyFn, *, actor_id: str = "vla-planner-1", model_name: str = "lerobot") -> None:
        self.policy = policy
        self.actor_id = text(actor_id, "actor_id")
        self.model_name = text(model_name, "model_name")

    def propose(self, evidence: EvidenceFrame, scenario: str = "live") -> ProposedAction:
        result = self.policy(evidence)
        if not isinstance(result, Mapping):
            raise TypeError("policy output must be a mapping")
        raw = plain(result)
        missing = {"action_type", "object_id", "target_bin", "speed_mps", "trajectory"} - raw.keys()
        if missing:
            raise ValueError("missing required action fields: " + ", ".join(sorted(missing)))
        return ProposedAction.pick_place(
            evidence.evidence_id, actor_id=self.actor_id,
            action_type=text(raw["action_type"], "action_type"),
            target_bin=text(raw["target_bin"], "target_bin"),
            object_id=text(raw["object_id"], "object_id"),
            speed_mps=number(raw["speed_mps"], "speed_mps", minimum=0.0),
            trajectory=trajectory(raw["trajectory"]),
            metadata={"planner": "lerobot-vla", "model": self.model_name,
                      "source_frame_hash": evidence.frame_hash, "source_evidence_id": evidence.evidence_id},
        )


class MuJoCoActuator:
    """Wrap an execution callback without manufacturing a success result."""

    def __init__(self, execute_fn: ExecuteFn) -> None:
        self.execute_fn = execute_fn

    def execute(self, action: ProposedAction) -> dict[str, object]:
        result = self.execute_fn(action)
        if not isinstance(result, Mapping):
            raise TypeError("MuJoCo callback must return a mapping")
        normalized = plain(result)
        normalized.setdefault("status", "UNKNOWN")
        normalized.setdefault("action_id", action.action_id)
        normalized.setdefault("object_id", action.object_id)
        normalized.setdefault("target_bin", action.target_bin)
        normalized.setdefault("speed_mps", action.speed_mps)
        return normalized
