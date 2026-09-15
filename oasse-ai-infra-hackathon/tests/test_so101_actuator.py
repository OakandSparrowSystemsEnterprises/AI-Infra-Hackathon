from __future__ import annotations

from dataclasses import replace

from oasse_physical_ai.models import ProposedAction, physically_changed
from oasse_physical_ai.providers.so101 import SO101Actuator


FEATURES = {
    "shoulder_pan.pos": float,
    "shoulder_lift.pos": float,
    "elbow_flex.pos": float,
    "wrist_flex.pos": float,
    "wrist_roll.pos": float,
    "gripper.pos": float,
}


class FakeRobot:
    action_features = FEATURES

    def __init__(self) -> None:
        self.calls: list[dict[str, float]] = []

    def send_action(self, action: dict[str, float]) -> dict[str, float]:
        self.calls.append(dict(action))
        return dict(action)

    def disconnect(self) -> None:
        pass


def joint_values() -> dict[str, float]:
    return {name: float(i) for i, name in enumerate(FEATURES)}


def action() -> ProposedAction:
    return ProposedAction.pick_place("ev-1", action_id="act-1", joint_action=joint_values())


def joints(_: ProposedAction) -> dict[str, float]:
    return joint_values()


def test_authorized_joint_action_reaches_robot_once() -> None:
    robot = FakeRobot()
    actuator = SO101Actuator(robot)

    result = actuator.execute_guarded(action(), lambda: None)

    assert result["status"] == "EXECUTED"
    assert result["action_id"] == "act-1"
    assert robot.calls == [joint_values()]


def test_guard_blocks_before_physical_send() -> None:
    robot = FakeRobot()
    actuator = SO101Actuator(robot)

    result = actuator.execute_guarded(action(), lambda: "EVIDENCE_EXPIRED_AT_DISPATCH")

    assert result == {
        "status": "NOT_EXECUTED",
        "reason": "EVIDENCE_EXPIRED_AT_DISPATCH",
        "action_id": "act-1",
    }
    assert robot.calls == []


def test_wrong_joint_shape_never_reaches_robot() -> None:
    robot = FakeRobot()
    bad = replace(action(), joint_action={"shoulder_pan.pos": 1.0})
    actuator = SO101Actuator(robot)

    try:
        actuator.execute(bad)
    except ValueError as exc:
        assert "action keys mismatch" in str(exc)
    else:
        raise AssertionError("expected invalid joint action to fail")

    assert robot.calls == []


def test_joint_action_is_a_physical_action_field() -> None:
    original = action()
    changed = dict(original.joint_action or {})
    changed["shoulder_pan.pos"] += 10.0
    transformed = replace(original, joint_action=changed)

    assert physically_changed(transformed, original)
