"""Native, optional OpenVINO inference over explicitly specified RGB frames.

Only load trusted local IR artifacts. Hash checks bind artifacts but do not
sandbox a model or establish that its predictions are correct.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import hmac
from pathlib import Path
import re
import stat
import threading
import time
from typing import Any, Callable, Mapping

from ..models import EvidenceFrame
from ..normalization import number, text
from .openvino_adapter import CapturedFrame, OpenVINOPerceptionProvider


@dataclass(frozen=True)
class RGBSpec:
    width: int = 96
    height: int = 96

    def __post_init__(self) -> None:
        if any(type(n) is not int or not 8 <= n <= 512 for n in (self.width, self.height)):
            raise ValueError("RGB dimensions must be integers in [8, 512]")

    @property
    def shape(self) -> tuple[int, int, int, int]:
        return (1, 3, self.height, self.width)

    def tensor(self, data: bytes) -> Any:
        import numpy as np
        if type(data) is not bytes or len(data) != self.width * self.height * 3:
            raise ValueError("expected exactly width * height * 3 raw RGB8 bytes")
        image = np.frombuffer(data, dtype=np.uint8).reshape(self.height, self.width, 3)
        return np.ascontiguousarray(image.transpose(2, 0, 1)[None], dtype=np.float32) / np.float32(255)


@dataclass(frozen=True)
class RGBFrame(CapturedFrame):
    width: int = 96
    height: int = 96
    workspace_clear: bool | None = None
    context_source: str = "unspecified"
    scene_hash: str | None = None
    object_pose_xyzrpy: tuple[float, ...] | None = None
    object_dimensions_xyz: tuple[float, ...] | None = None


def _read_regular(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        info = __import__("os").fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError("model artifact is not a bounded regular file")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("model artifact exceeds byte limit")
    return data


def artifact_digest(xml: bytes, weights: bytes) -> str:
    digest = hashlib.sha256(b"OASSE-OPENVINO-IR-v1\0")
    for part in (xml, weights):
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


class OpenVINOIRRunner:
    """Compile a frozen artifact once and copy every input/output at inference."""

    def __init__(self, xml_path: str | Path, spec: RGBSpec, *, device: str = "CPU",
                 expected_sha256: str | None = None) -> None:
        if not isinstance(spec, RGBSpec):
            raise TypeError("spec must be RGBSpec")
        if not isinstance(device, str) or re.fullmatch(r"(?:CPU|GPU|NPU)(?:\.[0-9]+)?", device) is None:
            raise ValueError("choose an explicit CPU, GPU or NPU device; no AUTO fallback")
        path = Path(xml_path)
        if path.suffix.lower() != ".xml":
            raise ValueError("expected OpenVINO IR .xml with a paired .bin")
        xml = _read_regular(path, 64 * 1024 * 1024)
        weights = _read_regular(path.with_suffix(".bin"), 512 * 1024 * 1024)
        if not xml:
            raise ValueError("empty IR definition")
        digest = artifact_digest(xml, weights)
        if expected_sha256 is not None:
            if not isinstance(expected_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
                raise ValueError("expected_sha256 must be lowercase hexadecimal SHA-256")
            if not hmac.compare_digest(digest, expected_sha256):
                raise ValueError("MODEL_ARTIFACT_HASH_MISMATCH")
        try:
            import openvino as ov
            import numpy as np
        except ImportError as exc:
            raise RuntimeError('Install perception extras with pip install -e ".[perception]"') from exc
        self.spec, self.device, self.model_sha256 = spec, device, digest
        self.ov, self.np = ov, np
        self.core = ov.Core()
        # Compile the bytes that were hashed, not a pathname which could change.
        self.model = self.core.read_model(xml, weights)
        if len(self.model.inputs) != 1:
            raise ValueError("native RGB runner requires exactly one input")
        port = self.model.input(0)
        if port.get_partial_shape().is_dynamic or tuple(port.shape) != spec.shape or port.get_element_type() != ov.Type.f32:
            raise ValueError("model input must be static float32 NCHW RGB matching RGBSpec")
        if not 1 <= len(self.model.outputs) <= 16:
            raise ValueError("unsupported model output count")
        for output in self.model.outputs:
            if output.get_partial_shape().is_dynamic or int(np.prod(output.shape)) > 1000000:
                raise ValueError("outputs must have bounded static shapes")
        config = {"PERFORMANCE_HINT": "LATENCY"}
        if device == "CPU":
            config.update({"INFERENCE_PRECISION_HINT": "f32", "INFERENCE_NUM_THREADS": 1})
        self.compiled = self.core.compile_model(self.model, device, config)
        self.execution_devices = [str(item) for item in self.compiled.get_property("EXECUTION_DEVICES")]
        if not self.execution_devices:
            raise RuntimeError("execution device was not reported")
        self._request = self.compiled.create_infer_request()
        self._lock = threading.Lock()
        self.calls = 0
        self.last_latency_ms = 0.0

    def infer(self, data: bytes) -> dict[str, Any]:
        tensor = self.spec.tensor(data)
        with self._lock:
            start = time.perf_counter_ns()
            raw = self._request.infer({0: tensor}, share_inputs=False, share_outputs=False)
            result = {}
            for index, port in enumerate(self.compiled.outputs):
                names = sorted(port.get_names())
                name = names[0] if names else f"output_{index}"
                if name in result:
                    raise ValueError("duplicate model output name")
                value = self.np.array(raw[port], copy=True)
                if not self.np.issubdtype(value.dtype, self.np.number) or not self.np.isfinite(value).all():
                    raise ValueError("model produced invalid numeric output")
                result[name] = value
            self.last_latency_ms = (time.perf_counter_ns() - start) / 1e6
            self.calls += 1
            return result

    def provenance(self) -> dict:
        return {"inference_backend": "openvino-native", "openvino_version": self.ov.__version__,
                "model_sha256": self.model_sha256, "requested_device": self.device,
                "execution_devices": list(self.execution_devices), "native_inference_calls": self.calls,
                "native_inference_ms": self.last_latency_ms, "input_layout": "NCHW-f32-RGB-div255"}


def export_reference_difference(reference_rgb: bytes, spec: RGBSpec, path: str | Path) -> str:
    """Export an authored pixel-difference graph, NOT a trained anomaly detector."""
    import openvino as ov
    from openvino import opset13 as ops
    import numpy as np
    reference = spec.tensor(reference_rgb)
    image = ops.parameter(spec.shape, np.float32, name="rgb")
    delta = ops.abs(ops.subtract(image, ops.constant(reference)))
    anomaly = ops.reduce_mean(delta, ops.constant(np.array([1], dtype=np.int64)), False)
    model = ov.Model([anomaly], [image], "reference_image_difference_not_trained")
    model.output(0).get_tensor().set_names({"anomaly_map"})
    path = Path(path)
    if path.suffix.lower() != ".xml":
        raise ValueError("IR output must end in .xml")
    path.parent.mkdir(parents=True, exist_ok=True)
    ov.serialize(model, str(path), str(path.with_suffix(".bin")))
    return artifact_digest(path.read_bytes(), path.with_suffix(".bin").read_bytes())


class ReferenceDifferenceDecoder:
    """Threshold exact image differences. Score is not a probability of defect."""

    def __init__(self, threshold: float = 0.10, *, confidence: float = 0.99) -> None:
        self.threshold = number(threshold, "threshold", minimum=0.000001, maximum=1)
        self.confidence = number(confidence, "confidence", minimum=0, maximum=1)

    def __call__(self, outputs: Mapping[str, Any], spec: RGBSpec) -> dict:
        import numpy as np
        value = outputs.get("anomaly_map")
        if value is None:
            raise ValueError("model did not provide anomaly_map")
        array = np.asarray(value)
        if array.shape != (1, spec.height, spec.width) or not np.isfinite(array).all():
            raise ValueError("invalid anomaly map")
        if float(array.min()) < 0 or float(array.max()) > 1.000001:
            raise ValueError("anomaly map must be in [0,1]")
        ys, xs = np.where(array[0] > self.threshold)
        box = None if len(xs) == 0 else [float(xs.min()/spec.width), float(ys.min()/spec.height),
                                       float((xs.max()+1)/spec.width), float((ys.max()+1)/spec.height)]
        score = min(1.0, float(array.max()))
        return {"confidence": self.confidence, "anomaly_score": score,
                "anomaly_bbox_xyxy": box, "target_label": "visually_changed_cube" if box else "reference_cube",
                "metadata": {"detector": "deterministic-reference-difference-not-trained",
                             "confidence_source": "declared-test-value-not-calibrated",
                             "difference_threshold": self.threshold}}


class NativeOpenVINOPerception:
    """Join real RGB inference with explicitly sourced non-visual context."""

    def __init__(self, frame_source: Any, runner: OpenVINOIRRunner,
                 decoder: Callable[[Mapping[str, Any], RGBSpec], Mapping[str, Any]]) -> None:
        self.frame_source, self.runner, self.decoder = frame_source, runner, decoder
        self._lock = threading.Lock()

    def observe(self, scenario: str = "live") -> EvidenceFrame:
        with self._lock:
            frame = self.frame_source.capture()
            if not isinstance(frame, RGBFrame):
                raise TypeError("native inference requires an RGBFrame")
            if (frame.width, frame.height) != (self.runner.spec.width, self.runner.spec.height):
                raise ValueError("frame dimensions do not match model contract")
            if type(frame.workspace_clear) is not bool or frame.context_source == "unspecified":
                raise ValueError("workspace context must be explicitly supplied, never guessed")
            text(frame.context_source, "context_source")
            data = bytes(frame.data)
            # Construct one immutable capture for both hashing and inference.
            captured = replace(frame, data=data)
            outputs = self.runner.infer(data)
            raw = dict(self.decoder(outputs, self.runner.spec))
            raw["workspace_clear"] = frame.workspace_clear
            raw["object_pose_xyzrpy"] = frame.object_pose_xyzrpy
            raw["object_dimensions_xyz"] = frame.object_dimensions_xyz
            meta = dict(raw.get("metadata", {}))
            meta.update({"context_source": frame.context_source, "geometry_source": frame.context_source,
                         "workspace_source": frame.context_source, "image_source": frame.camera_id})
            raw["metadata"] = meta
            class FixedFrame:
                def capture(self):
                    return captured
            evidence = OpenVINOPerceptionProvider(FixedFrame(), lambda _: raw).observe(scenario)
            return replace(evidence, scene_hash=frame.scene_hash,
                           metadata={**evidence.metadata, **self.runner.provenance()})
