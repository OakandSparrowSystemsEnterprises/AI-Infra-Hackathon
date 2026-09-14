"""Native cube sorting with an idealized Cartesian suction constraint.

The free cube moves through MuJoCo dynamics, including gravity and release.
The grip is an idealized weld, NOT an SO-101 finger-grasp or hardware model.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Callable

from ..models import ProposedAction
from ..normalization import number, trajectory

SORTING_XML = """<mujoco model="oasse_cartesian_suction_sorter">
  <option timestep="0.005" gravity="0 0 -9.81" integrator="implicitfast"/>
  <worldbody>
    <light pos="0 0 1.5"/>
    <geom name="table" type="plane" size="0.5 0.5 0.01" rgba="0.3 0.3 0.3 1"/>
    <body name="carrier" pos="0 0 0.18" gravcomp="1">
      <joint name="x" type="slide" axis="1 0 0" range="-0.4 0.4"/>
      <joint name="y" type="slide" axis="0 1 0" range="-0.4 0.4"/>
      <joint name="z" type="slide" axis="0 0 1" range="-0.13 0.22"/>
      <geom type="cylinder" size="0.009 0.01" mass="0.05" rgba="0.2 0.5 0.9 1"/>
    </body>
    <body name="cube" pos="0.18 0.12 0.025">
      <freejoint name="cube_free"/>
      <geom type="box" size="0.025 0.025 0.025" mass="0.01" friction="1 .005 .0001" rgba="0.8 0.5 0.2 1"/>
    </body>
    <site name="accept" pos="0.3 0.1 0.001" size="0.045 0.045 0.001" type="box" rgba="0.2 0.8 0.3 0.4"/>
    <site name="reject" pos="0.3 -0.1 0.001" size="0.045 0.045 0.001" type="box" rgba="0.8 0.2 0.3 0.4"/>
  </worldbody>
  <contact><exclude body1="carrier" body2="cube"/></contact>
  <equality><weld name="suction" body1="carrier" body2="cube" active="false"
                  relpose="0 0 -0.035 1 0 0 0" solref="0.01 1"/></equality>
  <actuator>
    <velocity joint="x" kv="50" ctrllimited="true" ctrlrange="-1 1"/>
    <velocity joint="y" kv="50" ctrllimited="true" ctrlrange="-1 1"/>
    <velocity joint="z" kv="50" ctrllimited="true" ctrlrange="-1 1"/>
  </actuator>
</mujoco>"""


class MuJoCoSortingRuntime:
    """Seven-waypoint pick/lift/place/release recipe, validated before dispatch."""

    BINS = {"accept": (.3, .1), "reject": (.3, -.1)}

    def __init__(self, *, max_steps: int = 5000) -> None:
        import mujoco
        import numpy as np
        if type(max_steps) is not int or not 1 <= max_steps <= 100000:
            raise ValueError("invalid step budget")
        self.mj, self.np = mujoco, np
        self.model = mujoco.MjModel.from_xml_string(SORTING_XML)
        self.data = mujoco.MjData(self.model)
        self.eq = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_EQUALITY, "suction")
        self.max_steps, self.step_count = max_steps, 0
        self.workspace_clear, self.anomaly_score = True, 0.0
        self.stage_callback: Callable[[str], None] | None = None
        mujoco.mj_forward(self.model, self.data)

    @property
    def position(self) -> list[float]:
        return (self.data.qpos[:3] + self.np.array([0., 0., .18])).tolist()

    @property
    def object_position(self) -> list[float]:
        return self.data.qpos[3:6].tolist()

    def state(self) -> dict:
        return {"qpos": self.data.qpos.tolist(), "qvel": self.data.qvel.tolist(),
                "sim_time_s": float(self.data.time), "steps": self.step_count,
                "grip_active": bool(self.data.eq_active[self.eq]),
                "workspace_clear": self.workspace_clear, "anomaly_score": self.anomaly_score}

    def state_bytes(self) -> bytes:
        return json.dumps(self.state(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

    def scene_hash(self) -> str:
        return hashlib.sha256(self.state_bytes()).hexdigest()

    def move_object(self, xyz: list[float]) -> None:
        """Explicit test-fixture disturbance. Never used by execute_guarded()."""
        self.data.qpos[3:6] = trajectory([xyz])[0]
        self.mj.mj_forward(self.model, self.data)

    def recipe(self, target_bin: str) -> list[list[float]]:
        if target_bin not in self.BINS:
            raise ValueError("unsupported bin")
        x, y, z = self.object_position
        bx, by = self.BINS[target_bin]
        grip_z = z + .035
        return [self.position, [x, y, .16], [x, y, grip_z], [x, y, .16],
                [bx, by, .16], [bx, by, .06], [bx, by, .16]]

    def verify(self, action: ProposedAction) -> dict:
        self.mj.mj_forward(self.model, self.data)
        x, y, z = self.object_position
        observed = None
        # Require the whole 5 cm cube footprint to lie inside the 9 cm bin.
        for name, (bx, by) in self.BINS.items():
            if abs(x-bx) <= .019 and abs(y-by) <= .019 and .02 <= z <= .03:
                observed = name
        return {"observed_at_ms": int(time.time()*1000), "observation_source": "mujoco-body-state",
                "object_id": "cube-1", "observed_bin": observed,
                "object_released": not bool(self.data.eq_active[self.eq]),
                "object_position_xyz": self.object_position,
                "object_speed_mps": float(self.np.linalg.norm(self.data.qvel[3:6]))}

    def execute(self, action: ProposedAction) -> dict:
        return self.execute_guarded(action, lambda: None)

    def execute_guarded(self, action: ProposedAction, check: Callable[[], str | None]) -> dict:
        before = self.object_position
        before_steps = self.step_count
        peak_command = peak_measured = 0.0
        events: list[str] = []
        def answer(status, reason):
            return {"status": status, "reason": reason, "action_id": action.action_id,
                    "backend": "mujoco", "model": "cartesian-idealized-suction",
                    "speed_mps": action.speed_mps, "simulation_steps": self.step_count-before_steps,
                    "controller_speed_factor": .85,
                    "before_object_xyz": before, "after_object_xyz": self.object_position,
                    "peak_command_speed_mps": peak_command, "peak_measured_speed_mps": peak_measured,
                    "grip_active": bool(self.data.eq_active[self.eq]), "events": list(events),
                    "partial_effect_possible": status != "EXECUTED" and self.step_count > before_steps,
                    "physical_grasp_validated": False}
        try:
            points = trajectory(action.trajectory)
            speed = number(action.speed_mps, "speed_mps", minimum=.000001, maximum=1.)
            if action.action_type != "pick_place" or action.object_id != "cube-1":
                raise ValueError("unsupported primitive")
            required = self.recipe(action.target_bin)
            if len(points) != 7 or not self.np.allclose(points, required, rtol=0, atol=.001):
                raise ValueError("trajectory differs from the declared pick/place recipe")
            if bool(self.data.eq_active[self.eq]) or self.np.linalg.norm(self.data.qvel) > .001:
                raise ValueError("sorter must begin at rest with a released object")
        except (TypeError, ValueError, OverflowError):
            return answer("NOT_EXECUTED", "SORT_RECIPE_INVALID")

        def step(control):
            nonlocal peak_command, peak_measured
            reason = check()
            if reason:
                return reason
            if not self.workspace_clear:
                return "WORKSPACE_BECAME_OCCUPIED"
            if self.step_count-before_steps >= self.max_steps:
                return "SIMULATOR_STEP_BUDGET"
            self.data.ctrl[:] = control
            # Gravity feed-forward for the attached cube; carrier has gravcomp=1.
            self.data.qfrc_applied[2] = .0981 if self.data.eq_active[self.eq] else 0.
            peak_command = max(peak_command, float(self.np.linalg.norm(self.data.ctrl)))
            self.mj.mj_step(self.model, self.data)
            self.step_count += 1
            if not self.np.isfinite(self.data.qpos).all() or not self.np.isfinite(self.data.qvel).all():
                raise ValueError("nonfinite physics state")
            peak_measured = max(peak_measured, float(self.np.linalg.norm(self.data.qvel[:3])))
            if peak_measured > speed + 1e-9:
                return "MEASURED_SPEED_EXCEEDED"
            return None

        def interrupt(reason):
            return answer("UNKNOWN" if self.step_count > before_steps else "NOT_EXECUTED", reason)
        try:
            for index, point in enumerate(points[1:], 1):
                if self.stage_callback:
                    self.stage_callback(f"waypoint_{index}")
                target = self.np.array(point)
                while True:
                    delta = target-self.np.array(self.position)
                    distance = float(self.np.linalg.norm(delta))
                    if distance <= .0005:
                        break
                    velocity = delta/distance * min(.85*speed, distance/float(self.model.opt.timestep))
                    reason = step(velocity)
                    if reason: return interrupt(reason)
                for _ in range(8):
                    reason = step(self.np.zeros(3))
                    if reason: return interrupt(reason)
                if index == 2:
                    reason = check()
                    if reason: return interrupt(reason)
                    grip_error = self.np.array(self.position)-self.np.array(self.object_position)-[0.,0.,.035]
                    if float(self.np.linalg.norm(grip_error)) > .003:
                        return interrupt("OBJECT_NOT_AT_GRIP_POINT")
                    self.data.eq_active[self.eq] = True
                    events.append("SUCTION_ATTACHED")
                if index == 5:
                    reason = check()
                    if reason: return interrupt(reason)
                    self.data.eq_active[self.eq] = False
                    events.append("OBJECT_RELEASED")
            for _ in range(80):
                reason = step(self.np.zeros(3))
                if reason: return interrupt(reason)
            self.mj.mj_forward(self.model, self.data)
            return answer("EXECUTED", "SORT_RECIPE_EXECUTED")
        except Exception as exc:
            result = interrupt("SIMULATOR_ERROR")
            result["error_type"] = type(exc).__name__
            return result
        finally:
            # No extra physics step is taken after permission has expired.
            self.data.ctrl[:] = 0.
            self.data.qfrc_applied[:] = 0.
