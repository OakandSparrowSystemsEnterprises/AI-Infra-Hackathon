from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from ..models import ProposedAction


class LeRobotArm(Protocol):
    @property
    def action_features(self) -> Mapping[str, object]: ...

    def send_action(self, action: dict[str, float]) -> Mapping[str, Any]: ...

    def disconnect(self) -> None: ...


JointActionMapper = Callable[[ProposedAction], Mapping[str, float]]


def _normalize_joint_action(robot: LeRobotArm, raw: Mapping[str, float]) -> dict[str, float]:
    if not isinstance(raw, Mapping) or not raw:
        raise TypeError("SO101 joint action must be a non-empty mapping")

    expected = {name for name in robot.action_features if name.endswith(".pos")}
    supplied = set(raw)
    if supplied != expected:
        missing = sorted(expected - supplied)
        extra = sorted(supplied - expected)
        raise ValueError(f"SO101 action keys mismatch: missing={missing}, extra={extra}")

    normalized: dict[str, float] = {}
    for name, value in raw.items():
        if type(value) not in (int, float):
            raise TypeError(f"{name} must be numeric")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        normalized[name] = value
    return normalized


def _metadata_joint_action(action: ProposedAction) -> Mapping[str, float]:
    raw = action.metadata.get("joint_action")
    if not isinstance(raw, Mapping):
        raise ValueError("authorized action is missing metadata.joint_action")
    return raw


class SO101Actuator:
    """Thin Gatekeeper-to-LeRobot execution boundary.

    The SO-101 command is carried inside the authorized ProposedAction metadata
    for this greenfield onsite adapter. ALLOW preserves the exact action object;
    HOLD/DENY never reach this class. A custom mapper can still be injected for
    tests or alternate sponsor bindings.
    """

    def __init__(self, robot: LeRobotArm, mapper: JointActionMapper | None = None) -> None:
        self.robot = robot
        self.mapper = _metadata_joint_action if mapper is None else mapper

    def execute(self, action: ProposedAction) -> dict[str, object]:
        return self.execute_guarded(action, lambda: None)

    def execute_guarded(
        self,
        action: ProposedAction,
        check_step: Callable[[], str | None],
    ) -> dict[str, object]:
        reason = check_step()
        if reason is not None:
            return {"status": "NOT_EXECUTED", "reason": reason, "action_id": action.action_id}

        requested = _normalize_joint_action(self.robot, self.mapper(action))

        reason = check_step()
        if reason is not None:
            return {"status": "NOT_EXECUTED", "reason": reason, "action_id": action.action_id}

        sent_raw = self.robot.send_action(dict(requested))
        sent = _normalize_joint_action(self.robot, sent_raw)
        return {
            "status": "EXECUTED",
            "action_id": action.action_id,
            "requested_joint_action": requested,
            "sent_joint_action": sent,
        }


def connect_event_so101(
    *,
    port: str,
    calibration_id: str = "hack_follower",
    calibrate: bool = False,
) -> Any:
    """Create and connect the event SO-101 without importing LeRobot on dev machines."""

    try:
        from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    except ImportError as exc:  # pragma: no cover - hardware environment only
        raise RuntimeError("LeRobot SO-101 follower API is not installed in this Python environment") from exc

    config = SO101FollowerConfig(port=port, id=calibration_id)
    robot = SO101Follower(config)
    robot.connect(calibrate=calibrate)
    return robot
