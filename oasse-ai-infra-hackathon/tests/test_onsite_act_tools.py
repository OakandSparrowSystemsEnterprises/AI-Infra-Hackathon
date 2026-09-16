from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


rollout = load_script("run_act_governed_rollout.py")
single = load_script("run_act_governed_single_step.py")


def test_parse_camera_source_accepts_index_or_path() -> None:
    assert rollout.parse_camera_source("12") == 12
    assert rollout.parse_camera_source("/dev/video1") == "/dev/video1"
    assert single.parse_camera_source("7") == 7
    assert single.parse_camera_source("/dev/video7") == "/dev/video7"


def test_parse_episode_ids() -> None:
    assert rollout.parse_episode_ids("5,6,8,9") == [5, 6, 8, 9]
    with pytest.raises(argparse.ArgumentTypeError):
        rollout.parse_episode_ids("5,5")
    with pytest.raises(argparse.ArgumentTypeError):
        rollout.parse_episode_ids("5,-1")
    with pytest.raises(argparse.ArgumentTypeError):
        rollout.parse_episode_ids("five")


def test_parse_caps_requires_six_positive_values() -> None:
    assert rollout.parse_caps("11.43,5,5,3.47,2.64,5") == [11.43, 5.0, 5.0, 3.47, 2.64, 5.0]
    with pytest.raises(argparse.ArgumentTypeError):
        rollout.parse_caps("1,2,3")
    with pytest.raises(argparse.ArgumentTypeError):
        rollout.parse_caps("1,2,3,4,5,0")


def test_envelope_digest_is_order_independent_for_joint_map() -> None:
    first = {"shoulder_pan.pos": 1.0, "gripper.pos": 2.0}
    second = {"gripper.pos": 2.0, "shoulder_pan.pos": 1.0}
    assert rollout.envelope_digest("a", "e", first) == rollout.envelope_digest("a", "e", second)
    assert rollout.envelope_digest("a", "e", first) != rollout.envelope_digest("b", "e", first)
