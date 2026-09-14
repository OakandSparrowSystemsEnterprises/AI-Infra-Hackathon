from __future__ import annotations

"""LeRobot/MuJoCo integration seams implemented independently for this repo.

The external lerobot-mujoco tutorial is used as a reference for simulation
workflow only. No source from that repository is vendored here.
"""

import math
from typing import Any, Callable, Dict, Mapping

from ..models import EvidenceFrame, ProposedAction


PolicyFn = Callable[[EvidenceFrame], Mapping[str, Any]]
ExecuteFn = Callable[[ProposedAction], Mapping[str, Any]]


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{name} must be a non-empty string")
    return value


def _speed(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("speed_mps must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("speed_mps must be finite and non-negative")
    return result


def _trajectory(value: Any) -> list[list[float]]:
    if not isinstance(value, list) or not value:
        raise TypeError("trajectory must be a non-empty list")
    normalized: list[list[float]] = []
    for point in value:
        if not isinstance(point, list) or not point:
            raise TypeError("trajectory points must be non-empty lists")
        coords: list[float] = []
        for coordinate in point:
            if isinstance(coordinate, bool) or not isinstance(coordinate, (int, float)):
                raise TypeError("trajectory coordinates must be numeric")
            number = float(coordinate)
            if not math.isfinite(number):
                raise ValueError("trajectory coordinates must be finite")
            coords.append(number)
        normalized.append(coords)
    return normalized


class LeRobotVLAProvider:
    """Turn a LeRobot/VLA policy result into a proposal, never an authorization."""

    def __init__(self, policy: PolicyFn, *, actor_id: str = "lerobot-vla-1", model_name: str = "lerobot") -> None:
        self.policy = policy
        self.actor_id = _text(actor_id, "actor_id")
        self.model_name = _text(model_name, "model_name")

    def propose(self, evidence: EvidenceFrame, scenario: str = "live") -> ProposedAction:
        raw = dict(self.policy(evidence))
        target_bin = _text(raw.get("target_bin", "accept"), "target_bin")
        action_type = _text(raw.get("action_type", "pick_place"), "action_type")
        object_id = _text(raw.get("object_id", "cube-1"), "object_id")
        speed_mps = _speed(raw.get("speed_mps", 0.20))
        trajectory = _trajectory(raw.get("trajectory", [[0.0, 0.0, 0.0], [0.2, 0.0, 0.1]]))
        return ProposedAction.pick_place(
            evidence.evidence_id,
            actor_id=self.actor_id,
            action_type=action_type,
            target_bin=target_bin,
            speed_mps=speed_mps,
            object_id=object_id,
            trajectory=trajectory,
            metadata={
                "planner": "lerobot-vla",
                "model": self.model_name,
                "source_frame_hash": evidence.frame_hash,
                "source_evidence_id": evidence.evidence_id,
            },
        )


class MuJoCoActuator:
    """Execute an already-authorized ProposedAction in a MuJoCo environment."""

    def __init__(self, execute_fn: ExecuteFn) -> None:
        self.execute_fn = execute_fn

    def execute(self, action: ProposedAction) -> Dict[str, object]:
        result = self.execute_fn(action)
        if not isinstance(result, Mapping):
            raise TypeError("MuJoCo execute callback must return a mapping")
        normalized: Dict[str, object] = dict(result)
        normalized.setdefault("status", "EXECUTED")
        normalized.setdefault("action_id", action.action_id)
        normalized.setdefault("object_id", action.object_id)
        normalized.setdefault("target_bin", action.target_bin)
        normalized.setdefault("speed_mps", action.speed_mps)
        return normalized
