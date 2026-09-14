"""Rendered MuJoCo RGB capture, with explicitly labeled simulator context."""
from __future__ import annotations

import hashlib
import json
import threading
import time

from .mujoco_runtime import MuJoCoCartesianRuntime
from .openvino_runtime import RGBFrame, RGBSpec


class MuJoCoRGBCamera:
    """Render actual pixels. A black mark is a visual-only defect fixture.

    Physics and rendering are used serially in the demo. This class is not a
    cross-process simulator lock or a physical camera driver.
    """

    def __init__(self, runtime: MuJoCoCartesianRuntime, spec: RGBSpec = RGBSpec()) -> None:
        self.runtime, self.spec = runtime, spec
        self._owner_thread = threading.get_ident()
        self._closed = False
        self._sequence = 0
        self.marked = False
        mj = runtime.mj
        self.renderer = mj.Renderer(runtime.model, height=spec.height, width=spec.width)
        self.camera = mj.MjvCamera()
        self.camera.lookat[:] = [.18, .12, .025]
        self.camera.distance = .25
        self.camera.azimuth = 90
        self.camera.elevation = -90

    def scene_hash(self) -> str:
        payload = {"physics": self.runtime.scene_hash(), "black_mark": self.marked,
                   "view": {"lookat": self.camera.lookat.tolist(), "distance": float(self.camera.distance),
                            "azimuth": float(self.camera.azimuth), "elevation": float(self.camera.elevation)}}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

    def capture(self) -> RGBFrame:
        if self._closed:
            raise RuntimeError("camera is closed")
        if threading.get_ident() != self._owner_thread:
            raise RuntimeError("render context must be used by its owner thread")
        if type(self.marked) is not bool:
            raise TypeError("mark fixture must be boolean")
        before = self.scene_hash()
        captured = int(time.time() * 1000)
        self.renderer.update_scene(self.runtime.data, camera=self.camera)
        if self.marked:
            scene = self.renderer.scene
            if scene.ngeom >= scene.maxgeom:
                raise RuntimeError("no room for visual defect fixture")
            position = self.runtime.model.body("cube").pos.copy()
            position[2] += .0253
            self.runtime.mj.mjv_initGeom(scene.geoms[scene.ngeom], self.runtime.mj.mjtGeom.mjGEOM_BOX,
                self.runtime.np.array([.008, .008, .0002]), position,
                self.runtime.np.eye(3).reshape(9), self.runtime.np.array([0., 0., 0., 1.], dtype=self.runtime.np.float32))
            scene.ngeom += 1
        pixels = self.renderer.render().copy()
        if before != self.scene_hash():
            raise RuntimeError("scene changed during capture")
        if pixels.shape != (self.spec.height, self.spec.width, 3) or pixels.dtype != self.runtime.np.uint8:
            raise ValueError("renderer returned an unexpected RGB format")
        self._sequence += 1
        pose = tuple(float(x) for x in self.runtime.model.body("cube").pos) + (0., 0., 0.)
        return RGBFrame(data=pixels.tobytes(order="C"), captured_at_ms=captured,
            camera_id="mujoco-rgb-camera", sequence=self._sequence,
            width=self.spec.width, height=self.spec.height,
            workspace_clear=self.runtime.workspace_clear, context_source="simulator-ground-truth",
            scene_hash=before, object_pose_xyzrpy=pose, object_dimensions_xyz=(.05, .05, .05))

    def close(self) -> None:
        if not self._closed:
            self.renderer.close()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
