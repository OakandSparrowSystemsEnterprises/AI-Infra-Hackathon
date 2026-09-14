from __future__ import annotations

import pytest

from oasse_physical_ai.models import EvidenceFrame, ProposedAction
from oasse_physical_ai.providers.openvino_runtime import RGBSpec
from oasse_physical_ai.providers.sponsor_bridge import (
    SponsorActuator,
    SponsorGuardedActuator,
    SponsorRGBSource,
    SponsorVLAProvider,
    resolve_callable,
)


def test_resolve_callable_requires_explicit_entrypoint():
    assert resolve_callable("math:sqrt")(9) == 3
    with pytest.raises(ValueError):
        resolve_callable("math.sqrt")
    with pytest.raises(ValueError):
        resolve_callable("__import__('os'):system")


def test_sponsor_rgb_source_normalizes_explicit_frame_contract():
    spec = RGBSpec(width=8, height=8)
    payload = bytes(range(192))
    source = SponsorRGBSource(
        lambda: {
            "data": payload,
            "captured_at_ms": 1000,
            "workspace_clear": True,
            "context_source": "intel-camera-calibration-v1",
            "camera_id": "intel-camera-0",
            "sequence": 4,
            "width": 8,
            "height": 8,
            "object_pose_xyzrpy": [0.1, 0.2, 0.3, 0, 0, 0],
            "object_dimensions_xyz": [0.05, 0.05, 0.05],
            "scene_hash": "scene-4",
        },
        spec,
        camera_id="fallback-camera",
    )
    frame = source.capture()
    assert frame.data == payload
    assert frame.camera_id == "intel-camera-0"
    assert frame.sequence == 4
    assert frame.workspace_clear is True
    assert frame.context_source == "intel-camera-calibration-v1"


def test_sponsor_rgb_source_refuses_missing_workspace_facts():
    spec = RGBSpec(width=8, height=8)
    source = SponsorRGBSource(
        lambda: {"data": bytes(192), "captured_at_ms": 1000},
        spec,
        camera_id="camera",
    )
    with pytest.raises(TypeError):
        source.capture()


def test_sponsor_vla_provider_binds_exact_evidence_and_requires_motion_fields():
    evidence = EvidenceFrame.fresh(frame_hash="frame-1")
    provider = SponsorVLAProvider(
        lambda _: {
            "action_type": "pick_place",
            "object_id": "cube-1",
            "target_bin": "accept",
            "speed_mps": 0.2,
            "trajectory": [[0, 0, 0.05], [0.1, 0, 0.05]],
        },
        planner_name="physical-ai-studio",
        model_name="onsite-vla",
    )
    action = provider.propose(evidence)
    assert action.evidence_id == evidence.evidence_id
    assert action.metadata["planner"] == "physical-ai-studio"
    assert action.metadata["source_frame_hash"] == "frame-1"

    rebound = SponsorVLAProvider(
        lambda _: {
            "evidence_id": "wrong",
            "action_type": "pick_place",
            "object_id": "cube-1",
            "target_bin": "accept",
            "speed_mps": 0.2,
            "trajectory": [[0, 0, 0.05], [0.1, 0, 0.05]],
        }
    )
    with pytest.raises(ValueError):
        rebound.propose(evidence)


def test_sponsor_actuator_requires_explicit_command_binding():
    action = ProposedAction.pick_place("ev-1", action_id="act-1")
    actuator = SponsorActuator(
        lambda command: {"result": "ok", "command_id": command["action_id"]},
        status_key="result",
        action_id_key="command_id",
        status_map={"ok": "EXECUTED"},
    )
    result = actuator.execute(action)
    assert result["status"] == "EXECUTED"
    assert result["action_id"] == "act-1"

    wrong = SponsorActuator(
        lambda command: {"status": "EXECUTED", "action_id": "act-other"}
    )
    with pytest.raises(ValueError):
        wrong.execute(action)


def test_guarded_sponsor_actuator_receives_continuous_authority_hook():
    action = ProposedAction.pick_place("ev-1", action_id="act-guarded")
    seen = {}

    def execute(command, still_authorized):
        seen["command"] = command
        seen["guard_result"] = still_authorized()
        return {"status": "EXECUTED", "action_id": command["action_id"]}

    actuator = SponsorGuardedActuator(execute)
    result = actuator.execute_guarded(action, lambda: None)
    assert seen["guard_result"] is None
    assert seen["command"]["action_id"] == "act-guarded"
    assert result["status"] == "EXECUTED"
