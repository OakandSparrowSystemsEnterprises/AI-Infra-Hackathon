"""Strict sponsor-facing bridges for onsite integration.

These adapters keep sponsor SDKs outside the authority core. Sponsor code may
capture, infer, plan, or execute, but it does not bypass evidence binding,
Gatekeeper, dispatch freshness, replay protection, or receipt semantics.
"""
from __future__ import annotations

from collections.abc import Mapping
import importlib
import re
from typing import Any, Callable

from ..models import EvidenceFrame, ProposedAction
from ..normalization import integer, number, plain, text, trajectory, vector
from .openvino_runtime import RGBFrame, RGBSpec

_ENTRYPOINT = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*:"
    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
)
_EXECUTION_STATUSES = {"EXECUTED", "NOT_EXECUTED", "FAILED", "UNKNOWN"}


def resolve_callable(spec: str) -> Callable[..., Any]:
    """Resolve an explicit ``module:attribute`` entry point without eval."""
    if not isinstance(spec, str) or len(spec) > 256 or _ENTRYPOINT.fullmatch(spec) is None:
        raise ValueError("entrypoint must be a bounded module:attribute reference")
    module_name, attribute_path = spec.split(":", 1)
    value: Any = importlib.import_module(module_name)
    for part in attribute_path.split("."):
        value = getattr(value, part)
    if not callable(value):
        raise TypeError(f"{spec} does not resolve to a callable")
    return value


class SponsorRGBSource:
    """Normalize a sponsor camera callback into the repository RGBFrame contract.

    The callback may return RGBFrame directly or a mapping containing raw RGB8
    bytes under ``data`` (or a HxWx3 uint8 array under ``rgb``). Workspace and
    timing context must be explicit; the bridge does not invent safety facts.
    """

    def __init__(self, capture_fn: Callable[[], Any], spec: RGBSpec, *, camera_id: str) -> None:
        if not callable(capture_fn):
            raise TypeError("capture_fn must be callable")
        if not isinstance(spec, RGBSpec):
            raise TypeError("spec must be RGBSpec")
        self.capture_fn = capture_fn
        self.spec = spec
        self.camera_id = text(camera_id, "camera_id")
        self._sequence = 0

    def capture(self) -> RGBFrame:
        value = self.capture_fn()
        if isinstance(value, RGBFrame):
            return self._validate_frame(value)
        if not isinstance(value, Mapping):
            raise TypeError("sponsor camera must return RGBFrame or a mapping")

        raw = value
        if "data" in raw:
            data_value = raw["data"]
            if isinstance(data_value, (bytearray, memoryview)):
                data = bytes(data_value)
            elif type(data_value) is bytes:
                data = data_value
            else:
                raise TypeError("camera data must be raw RGB8 bytes")
        elif "rgb" in raw:
            import numpy as np

            array = np.asarray(raw["rgb"])
            if array.dtype != np.uint8 or array.shape != (self.spec.height, self.spec.width, 3):
                raise ValueError("rgb array must be uint8 HxWx3 matching RGBSpec")
            data = np.ascontiguousarray(array).tobytes()
        else:
            raise ValueError("sponsor camera output requires data or rgb")

        captured = integer(plain(raw.get("captured_at_ms")), "captured_at_ms")
        clear = plain(raw.get("workspace_clear"))
        if type(clear) is not bool:
            raise TypeError("workspace_clear must be an explicit boolean")
        context_source = text(raw.get("context_source"), "context_source")
        if context_source == "unspecified":
            raise ValueError("context_source must identify the source of workspace facts")

        width = integer(plain(raw.get("width", self.spec.width)), "width")
        height = integer(plain(raw.get("height", self.spec.height)), "height")
        if (width, height) != (self.spec.width, self.spec.height):
            raise ValueError("camera dimensions do not match RGBSpec")

        sequence_value = raw.get("sequence")
        if sequence_value is None:
            self._sequence += 1
            sequence = self._sequence
        else:
            sequence = integer(plain(sequence_value), "sequence")
            if sequence <= self._sequence:
                raise ValueError("sponsor camera sequence must increase")
            self._sequence = sequence

        scene_hash_value = raw.get("scene_hash")
        scene_hash = None if scene_hash_value is None else text(scene_hash_value, "scene_hash")

        pose_value = raw.get("object_pose_xyzrpy")
        pose = None if pose_value is None else tuple(
            vector(plain(pose_value), "object_pose_xyzrpy", 6)
        )
        dimensions_value = raw.get("object_dimensions_xyz")
        dimensions = None
        if dimensions_value is not None:
            dimensions = tuple(vector(plain(dimensions_value), "object_dimensions_xyz", 3))
            if any(value <= 0 for value in dimensions):
                raise ValueError("object dimensions must be positive")

        frame = RGBFrame(
            data=data,
            captured_at_ms=captured,
            camera_id=text(raw.get("camera_id", self.camera_id), "camera_id"),
            sequence=sequence,
            width=width,
            height=height,
            workspace_clear=clear,
            context_source=context_source,
            scene_hash=scene_hash,
            object_pose_xyzrpy=pose,
            object_dimensions_xyz=dimensions,
        )
        return self._validate_frame(frame)

    def _validate_frame(self, frame: RGBFrame) -> RGBFrame:
        if (frame.width, frame.height) != (self.spec.width, self.spec.height):
            raise ValueError("frame dimensions do not match RGBSpec")
        if type(frame.data) is not bytes or len(frame.data) != frame.width * frame.height * 3:
            raise ValueError("frame must contain exact RGB8 bytes")
        integer(frame.captured_at_ms, "captured_at_ms")
        if frame.sequence is not None:
            integer(frame.sequence, "sequence")
        text(frame.camera_id, "camera_id")
        if type(frame.workspace_clear) is not bool:
            raise TypeError("workspace_clear must be an explicit boolean")
        if frame.context_source == "unspecified":
            raise ValueError("context_source must identify the source of workspace facts")
        return frame


class SponsorVLAProvider:
    """Normalize a sponsor planner/VLA proposal without inventing motion fields."""

    def __init__(
        self,
        plan_fn: Callable[[EvidenceFrame], Any],
        *,
        actor_id: str = "vla-planner-1",
        planner_name: str = "sponsor-vla",
        model_name: str = "onsite-model",
    ) -> None:
        if not callable(plan_fn):
            raise TypeError("plan_fn must be callable")
        self.plan_fn = plan_fn
        self.actor_id = text(actor_id, "actor_id")
        self.planner_name = text(planner_name, "planner_name")
        self.model_name = text(model_name, "model_name")

    def propose(self, evidence: EvidenceFrame, scenario: str = "live") -> ProposedAction:
        result = self.plan_fn(evidence)
        if not isinstance(result, Mapping):
            raise TypeError("sponsor planner output must be a mapping")
        raw = plain(result)
        required = {"action_type", "object_id", "target_bin", "speed_mps", "trajectory"}
        missing = required - raw.keys()
        if missing:
            raise ValueError("missing required action fields: " + ", ".join(sorted(missing)))

        supplied_evidence = raw.get("evidence_id")
        if supplied_evidence is not None and text(supplied_evidence, "evidence_id") != evidence.evidence_id:
            raise ValueError("planner rebound proposal to different evidence")

        metadata = raw.get("metadata", {})
        if not isinstance(metadata, dict):
            raise TypeError("planner metadata must be an object")

        kwargs: dict[str, Any] = {}
        if raw.get("action_id") is not None:
            kwargs["action_id"] = text(raw["action_id"], "action_id")
        if raw.get("requested_at_ms") is not None:
            kwargs["requested_at_ms"] = integer(
                plain(raw["requested_at_ms"]), "requested_at_ms"
            )

        return ProposedAction.pick_place(
            evidence.evidence_id,
            actor_id=self.actor_id,
            action_type=text(raw["action_type"], "action_type"),
            object_id=text(raw["object_id"], "object_id"),
            target_bin=text(raw["target_bin"], "target_bin"),
            speed_mps=number(raw["speed_mps"], "speed_mps", minimum=0.0),
            trajectory=trajectory(raw["trajectory"]),
            metadata={
                **metadata,
                "planner": self.planner_name,
                "model": self.model_name,
                "source_evidence_id": evidence.evidence_id,
                "source_frame_hash": evidence.frame_hash,
            },
            **kwargs,
        )


class SponsorActuator:
    """Map an authorized action to a sponsor robot callback.

    The sponsor callback receives a detached JSON-native command. It must return
    an explicit status and action identifier. The bridge never manufactures an
    EXECUTED acknowledgement.
    """

    def __init__(
        self,
        execute_fn: Callable[[Mapping[str, Any]], Any],
        *,
        status_key: str = "status",
        action_id_key: str = "action_id",
        status_map: Mapping[str, str] | None = None,
    ) -> None:
        if not callable(execute_fn):
            raise TypeError("execute_fn must be callable")
        self.execute_fn = execute_fn
        self.status_key = text(status_key, "status_key")
        self.action_id_key = text(action_id_key, "action_id_key")
        mapping = {} if status_map is None else dict(status_map)
        self.status_map = {
            text(key, "status_map key"): text(value, "status_map value").upper()
            for key, value in mapping.items()
        }
        if any(value not in _EXECUTION_STATUSES for value in self.status_map.values()):
            raise ValueError("status_map values must use canonical execution statuses")

    @staticmethod
    def command(action: ProposedAction) -> dict[str, Any]:
        return {
            "action_id": action.action_id,
            "actor_id": action.actor_id,
            "action_type": action.action_type,
            "object_id": action.object_id,
            "target_bin": action.target_bin,
            "speed_mps": action.speed_mps,
            "trajectory": [list(point) for point in action.trajectory],
            "evidence_id": action.evidence_id,
            "requested_at_ms": action.requested_at_ms,
        }

    def execute(self, action: ProposedAction) -> dict[str, Any]:
        return self._normalize(self.execute_fn(self.command(action)), action)

    def _normalize(self, result: Any, action: ProposedAction) -> dict[str, Any]:
        if not isinstance(result, Mapping):
            raise TypeError("sponsor actuator must return a mapping")
        raw = plain(result)
        if self.status_key not in raw or self.action_id_key not in raw:
            raise ValueError("actuator acknowledgement requires status and action id")

        source_status = text(raw[self.status_key], self.status_key)
        status = self.status_map.get(source_status, source_status.upper())
        if status not in _EXECUTION_STATUSES:
            raise ValueError("unrecognized actuator status")
        action_id = text(raw[self.action_id_key], self.action_id_key)
        if status == "EXECUTED" and action_id != action.action_id:
            raise ValueError("executed acknowledgement is bound to a different action")

        normalized = dict(raw)
        normalized["status"] = status
        normalized["action_id"] = action_id
        normalized["binding_source"] = "sponsor-returned-action-id"
        return normalized


class SponsorGuardedActuator(SponsorActuator):
    """Sponsor actuator with an explicit continuous-authority callback seam."""

    def __init__(
        self,
        execute_guarded_fn: Callable[[Mapping[str, Any], Callable[[], str | None]], Any],
        **kwargs: Any,
    ) -> None:
        if not callable(execute_guarded_fn):
            raise TypeError("execute_guarded_fn must be callable")
        self.execute_guarded_fn = execute_guarded_fn
        super().__init__(
            lambda command: {"status": "UNKNOWN", "action_id": command["action_id"]},
            **kwargs,
        )

    def execute_guarded(
        self,
        action: ProposedAction,
        still_authorized: Callable[[], str | None],
    ) -> dict[str, Any]:
        if not callable(still_authorized):
            raise TypeError("still_authorized must be callable")
        return self._normalize(
            self.execute_guarded_fn(self.command(action), still_authorized),
            action,
        )
