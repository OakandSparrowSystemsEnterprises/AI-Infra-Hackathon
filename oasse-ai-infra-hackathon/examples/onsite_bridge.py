"""Local sponsor SDK bridge template.

Copy/scaffold this file into the ignored ``onsite/`` directory, then replace
only the function bodies needed for the event-provided Intel stack. Do not put
tokens or proprietary sponsor source in this repository.
"""


def capture_rgb():
    """Return sponsor camera output accepted by SponsorRGBSource.

    Minimum mapping:
    {
      "data": <raw RGB8 bytes>,
      "captured_at_ms": <int>,
      "workspace_clear": <bool>,
      "context_source": <str>
    }

    Optional: camera_id, sequence, width, height, scene_hash,
    object_pose_xyzrpy, object_dimensions_xyz.
    """
    raise NotImplementedError("bind event camera SDK here")


def read_context():
    """Return any separately sourced workspace/geometry context."""
    raise NotImplementedError("bind event workspace/context source here")


def plan(evidence):
    """Return the sponsor VLA/planner proposal.

    Required keys:
    action_type, object_id, target_bin, speed_mps, trajectory.
    """
    raise NotImplementedError("bind Physical AI Studio / LeRobot / VLA here")


def execute(command):
    """Send the already-authorized command to the robot/controller.

    Return an explicit status and the exact correlated action/command ID.
    Do not convert an ambiguous acknowledgement into EXECUTED.
    """
    raise NotImplementedError("bind final robot send API here")


def stop():
    """Invoke the sponsor-supported stop/cancel path if software-accessible."""
    raise NotImplementedError("bind controller stop/cancel API here")
