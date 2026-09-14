"""Native MuJoCo Cartesian-motion harness, not an SO-101 or grasping model.

All scene geometry is authored here. Observations are explicitly simulator
state, not OpenVINO detections. The policy integration remains independent.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Callable

from ..models import EvidenceFrame, ProposedAction
from ..normalization import number, trajectory

SCENE_XML = """<mujoco model="oasse_cartesian_authority_harness">
  <option timestep="0.005" gravity="0 0 0" integrator="implicitfast"/>
  <worldbody>
    <light pos="0 0 1.5"/>
    <geom name="table" type="plane" size="0.5 0.5 0.01" rgba="0.3 0.3 0.3 1"/>
    <body name="carrier" pos="0 0 0.05">
      <joint name="x" type="slide" axis="1 0 0" range="-0.4 0.4"/>
      <joint name="y" type="slide" axis="0 1 0" range="-0.4 0.4"/>
      <joint name="z" type="slide" axis="0 0 1" range="0 0.4"/>
      <geom type="sphere" size="0.015" mass="0.05" rgba="0.2 0.5 0.9 1"/>
    </body>
    <body name="cube" pos="0.18 0.12 0.025">
      <geom type="box" size="0.025 0.025 0.025" rgba="0.8 0.5 0.2 1"/>
    </body>
    <site name="accept" pos="0.3 0.1 0.001" size="0.04 0.04 0.001" type="box" rgba="0.2 0.8 0.3 0.4"/>
    <site name="reject" pos="0.3 -0.1 0.001" size="0.04 0.04 0.001" type="box" rgba="0.8 0.2 0.3 0.4"/>
  </worldbody>
  <actuator>
    <velocity joint="x" kv="20" ctrllimited="true" ctrlrange="-1 1"/>
    <velocity joint="y" kv="20" ctrllimited="true" ctrlrange="-1 1"/>
    <velocity joint="z" kv="20" ctrllimited="true" ctrlrange="-1 1"/>
  </actuator>
</mujoco>"""


class MuJoCoCartesianRuntime:
    """Apply bounded velocity controls using mj_step, never by teleporting qpos."""

    def __init__(self, *, max_steps: int = 10000) -> None:
        try:
            import mujoco
            import numpy as np
        except ImportError as exc:
            raise RuntimeError('Install the simulator extra: pip install -e ".[simulator]"') from exc
        if type(max_steps) is not int or not 1 <= max_steps <= 100000:
            raise ValueError("max_steps must be in [1, 100000]")
        self.mj, self.np = mujoco, np
        self.model = mujoco.MjModel.from_xml_string(SCENE_XML)
        self.data = mujoco.MjData(self.model)
        self.max_steps = max_steps
        self.step_count = 0
        self.workspace_clear = True
        self.anomaly_score = 0.0
        mujoco.mj_forward(self.model, self.data)

    @property
    def position(self) -> list[float]:
        return (self.data.qpos[:3] + self.np.array([0.0, 0.0, 0.05])).tolist()

    def state(self) -> dict:
        return {"qpos": self.data.qpos.tolist(), "qvel": self.data.qvel.tolist(),
                "sim_time_s": float(self.data.time), "steps": self.step_count,
                "cube_xyz": self.model.body("cube").pos.tolist(),
                "workspace_clear": self.workspace_clear, "anomaly_score": self.anomaly_score}

    def state_bytes(self) -> bytes:
        return json.dumps(self.state(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

    def scene_hash(self) -> str:
        return hashlib.sha256(self.state_bytes()).hexdigest()

    def move_object(self, xyz: list[float]) -> None:
        points = trajectory([xyz])
        self.model.body("cube").pos[:] = points[0]
        self.mj.mj_forward(self.model, self.data)

    def execute(self, action: ProposedAction) -> dict:
        return self.execute_guarded(action, lambda: None)

    def execute_guarded(self, action: ProposedAction, still_authorized: Callable[[], str | None]) -> dict:
        """Check freshness again before every native physics step.

        On interruption, this simulation freezes without further steps. This
        behavior is NOT a physical robot's braking or emergency-stop model.
        """
        before_steps = self.step_count
        before = self.position
        started_sim = float(self.data.time)
        peak_command, peak_measured = 0.0, 0.0

        def result(status: str, reason: str) -> dict:
            return {"status": status, "reason": reason, "backend": "mujoco",
                    "model": "cartesian-motion-harness", "action_id": action.action_id,
                    "speed_mps": action.speed_mps, "before_xyz": before, "after_xyz": self.position,
                    "simulation_steps": self.step_count - before_steps,
                    "simulation_elapsed_s": float(self.data.time) - started_sim,
                    "peak_command_speed_mps": peak_command, "peak_measured_speed_mps": peak_measured,
                    "partial_effect_possible": status != "EXECUTED" and self.step_count > before_steps,
                    "grasping_tested": False}

        # Validate the complete trajectory before any control write or mj_step.
        try:
            points = trajectory(action.trajectory)
            speed = number(action.speed_mps, "speed_mps", minimum=0.000001, maximum=1.0)
            if action.action_type != "pick_place" or action.object_id != "cube-1" or action.target_bin not in {"accept", "reject"}:
                raise ValueError("unsupported action")
            if len(points) < 2 or self.np.linalg.norm(self.np.array(points[0]) - before) > 0.002:
                raise ValueError("trajectory must start at the observed carrier position")
            if any(not (-0.39 <= p[0] <= 0.39 and -0.39 <= p[1] <= 0.39 and 0.05 <= p[2] <= 0.44) for p in points):
                raise ValueError("trajectory outside simulator workspace")
            # Refuse a fresh command if an earlier run left the carrier moving.
            if self.np.linalg.norm(self.data.qvel) > 0.0001:
                raise ValueError("carrier is not at rest")
        except (TypeError, ValueError, OverflowError):
            return result("NOT_EXECUTED", "SIMULATOR_ACTION_INVALID")

        def step(control: object) -> str | None:
            nonlocal peak_command, peak_measured
            reason = still_authorized()
            if reason:
                return reason
            if self.step_count - before_steps >= self.max_steps:
                return "SIMULATOR_STEP_BUDGET"
            self.data.ctrl[:] = control
            peak_command = max(peak_command, float(self.np.linalg.norm(self.data.ctrl)))
            self.mj.mj_step(self.model, self.data)
            self.step_count += 1
            if not self.np.isfinite(self.data.qpos).all() or not self.np.isfinite(self.data.qvel).all():
                raise ValueError("non-finite simulator state")
            peak_measured = max(peak_measured, float(self.np.linalg.norm(self.data.qvel)))
            return None

        try:
            dt = float(self.model.opt.timestep)
            for point in points[1:]:
                target = self.np.array(point)
                while True:
                    delta = target - self.np.array(self.position)
                    distance = float(self.np.linalg.norm(delta))
                    if distance <= 0.001:
                        break
                    control = delta / distance * min(speed, distance / dt)
                    reason = step(control)
                    if reason:
                        status = "UNKNOWN" if self.step_count > before_steps else "NOT_EXECUTED"
                        return result(status, reason)
            # Resolve inertial motion through physics, not state reassignment.
            while self.np.linalg.norm(self.data.qvel) > 0.00001:
                reason = step(self.np.zeros(3))
                if reason:
                    return result("UNKNOWN", reason)
            if self.np.linalg.norm(self.np.array(self.position) - points[-1]) > 0.002:
                return result("FAILED", "SIMULATOR_TARGET_NOT_REACHED")
            return result("EXECUTED", "CARTESIAN_TRAJECTORY_COMPLETED")
        except Exception as exc:
            answer = result("UNKNOWN", "SIMULATOR_ERROR")
            answer["error_type"] = type(exc).__name__
            return answer
        finally:
            self.data.ctrl[:] = 0.0


class MuJoCoStatePerception:
    """Explicit simulator ground truth, not a camera or learned perception model."""

    def __init__(self, runtime: MuJoCoCartesianRuntime) -> None:
        self.runtime = runtime
        self._sequence = 0

    def observe(self, scenario: str = "allow") -> EvidenceFrame:
        self._sequence += 1
        captured = int(time.time() * 1000)
        data = self.runtime.state_bytes()
        digest = hashlib.sha256(data).hexdigest()
        return EvidenceFrame(
            evidence_id=f"sim-{self._sequence}-{captured}-{digest}",
            captured_at_ms=captured, confidence=1.0, workspace_clear=self.runtime.workspace_clear,
            anomaly_score=self.runtime.anomaly_score, camera_id="mujoco-state",
            frame_hash=digest, frame_sequence=self._sequence, scene_hash=digest,
            object_pose_xyzrpy=[*self.runtime.model.body("cube").pos.tolist(), 0.0, 0.0, 0.0],
            object_dimensions_xyz=[0.05, 0.05, 0.05],
            metadata={"provider": "mujoco-state-ground-truth", "payload_format": "state-json", "camera_inference": False},
        )
