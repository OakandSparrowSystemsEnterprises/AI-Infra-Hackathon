"""Optional physical RGB camera ingress with fresh, explicitly sourced context.

Capture timestamps bound the host acquisition interval, not sensor exposure
or unobservable camera buffering. No geometry/workspace facts are invented.
"""
from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Callable, Any

from ..normalization import integer, text, vector
from .openvino_runtime import RGBFrame, RGBSpec


@dataclass(frozen=True)
class CameraContext:
    observed_at_ms: int
    workspace_clear: bool
    source: str
    object_pose_xyzrpy: tuple[float, ...] | None = None
    object_dimensions_xyz: tuple[float, ...] | None = None
    scene_hash: str | None = None


class OpenCVRGBSource:
    """Read an explicitly selected local camera. No automatic fallback to mock."""

    def __init__(self, index: int, spec: RGBSpec, context: Callable[[], CameraContext], *,
                 camera_id: str, max_context_age_ms: int = 100, max_capture_ms: int = 500,
                 capture_factory: Callable[[int], Any] | None = None) -> None:
        if type(index) is not int or index < 0:
            raise ValueError("camera index must be a nonnegative integer")
        self.spec, self.context = spec, context
        self.camera_id = text(camera_id, "camera_id")
        self.max_context_age_ms = integer(max_context_age_ms, "max_context_age_ms")
        self.max_capture_ms = integer(max_capture_ms, "max_capture_ms")
        if not isinstance(spec, RGBSpec) or not self.max_capture_ms:
            raise ValueError("invalid camera contract")
        if capture_factory is None:
            try:
                import cv2
            except ImportError as exc:
                raise RuntimeError('Install camera extras: pip install -e ".[camera]"') from exc
            capture_factory = cv2.VideoCapture
        self._capture = capture_factory(index)
        if not self._capture.isOpened():
            self._capture.release()
            raise RuntimeError("camera failed to open")
        # Never silently resize; a model/calibration is resolution-dependent.
        self._capture.set(3, spec.width)
        self._capture.set(4, spec.height)
        self._sequence = 0
        self._closed = False
        self._lock = threading.Lock()

    def capture(self) -> RGBFrame:
        import numpy as np
        with self._lock:
            if self._closed:
                raise RuntimeError("camera is closed")
            before = int(time.time()*1000)
            started = time.monotonic_ns()
            context = self.context()
            if not isinstance(context, CameraContext):
                raise TypeError("camera requires CameraContext")
            integer(context.observed_at_ms, "context timestamp")
            text(context.source, "context source")
            if context.source == "unspecified" or type(context.workspace_clear) is not bool:
                raise ValueError("workspace context must be explicit")
            context_now = int(time.time()*1000)
            if not 0 <= context_now-context.observed_at_ms <= self.max_context_age_ms:
                raise ValueError("workspace context is stale or future-dated")
            pose = None if context.object_pose_xyzrpy is None else tuple(vector(list(context.object_pose_xyzrpy), "object_pose_xyzrpy", 6))
            dimensions = None
            if context.object_dimensions_xyz is not None:
                sizes = vector(list(context.object_dimensions_xyz), "object_dimensions_xyz", 3)
                if any(n <= 0 for n in sizes): raise ValueError("dimensions must be positive")
                dimensions = tuple(sizes)
            if context.scene_hash is not None:
                text(context.scene_hash, "scene_hash")
            ok, bgr = self._capture.read()
            after = int(time.time()*1000)
            elapsed = (time.monotonic_ns()-started)/1e6
            if not ok or not isinstance(bgr, np.ndarray):
                raise RuntimeError("camera did not return a frame")
            if bgr.dtype != np.uint8 or bgr.shape != (self.spec.height, self.spec.width, 3):
                raise ValueError("camera format differs from the declared RGB model input")
            if elapsed > self.max_capture_ms or not 0 <= after-context.observed_at_ms <= self.max_context_age_ms:
                raise ValueError("capture or context expired during acquisition")
            self._sequence += 1
            data = np.ascontiguousarray(bgr[:, :, ::-1]).tobytes()
            return RGBFrame(data=data, captured_at_ms=min(before, context.observed_at_ms),
                camera_id=self.camera_id, sequence=self._sequence, width=self.spec.width, height=self.spec.height,
                workspace_clear=context.workspace_clear, context_source=context.source,
                scene_hash=context.scene_hash, object_pose_xyzrpy=pose,
                object_dimensions_xyz=dimensions)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._capture.release()
                self._closed = True

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
