"""Non-actuating onsite preflight and operator-attestation validation."""
from __future__ import annotations

import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any
from urllib.parse import urlsplit

REQUIRED_ACCEPTANCE_FIELDS = (
    "hardware_operator_approval",
    "camera_calibration",
    "trained_detector",
    "trained_vla",
    "pre_send_interception",
    "normal_sort",
    "defective_sort",
    "safe_interruption",
    "video_recorded",
    "judge_repository_access",
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True, stderr=subprocess.STDOUT).strip()


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _https_endpoint(value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except (TypeError, ValueError):
        return False
    return parsed.scheme == "https" and bool(parsed.hostname) and not (
        parsed.username or parsed.password or parsed.query or parsed.fragment
    )


def _tenki_endpoint(value: str) -> bool:
    if not _https_endpoint(value):
        return False
    try:
        return urlsplit(value).path.rstrip("/").endswith("/derive")
    except (TypeError, ValueError):
        return False


def run_preflight(
    repo: Path,
    *,
    require_gatekeeper: bool = False,
    require_anomalib: bool = False,
    require_lerobot: bool = False,
    require_tenki: bool = False,
    camera_index: int | None = None,
) -> dict[str, Any]:
    """Inspect the local machine without sending any robot command.

    Camera capture is opt-in because opening a device is environmental I/O. No
    actuator interface is imported or called here.
    """
    repo = repo.resolve()
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}

    try:
        commit = _git(repo, "rev-parse", "HEAD")
        dirty = bool(_git(repo, "status", "--porcelain"))
        branch = _git(repo, "branch", "--show-current")
        checks["git_repository"] = True
        checks["clean_worktree"] = not dirty
        details.update({"commit": commit, "branch": branch, "dirty": dirty})
    except (OSError, subprocess.CalledProcessError) as exc:
        checks["git_repository"] = False
        checks["clean_worktree"] = False
        details["git_error_type"] = type(exc).__name__

    packages = {
        name: _package_version(name)
        for name in (
            "oasse-physical-ai-authority",
            "openvino",
            "mujoco",
            "numpy",
            "opencv-python-headless",
            "opencv-python",
            "anomalib",
            "lerobot",
        )
    }
    details["packages"] = packages
    checks["openvino_installed"] = packages["openvino"] is not None
    checks["mujoco_installed"] = packages["mujoco"] is not None
    checks["opencv_installed"] = bool(packages["opencv-python-headless"] or packages["opencv-python"])
    if require_anomalib:
        checks["anomalib_installed"] = packages["anomalib"] is not None
    if require_lerobot:
        checks["lerobot_installed"] = packages["lerobot"] is not None

    try:
        ov = importlib.import_module("openvino")
        devices = list(ov.Core().available_devices)
        details["openvino_devices"] = devices
        checks["openvino_runtime"] = bool(devices)
    except Exception as exc:  # environment probe: preserve only exception type
        details["openvino_error_type"] = type(exc).__name__
        details["openvino_devices"] = []
        checks["openvino_runtime"] = False

    try:
        importlib.import_module("mujoco")
        checks["mujoco_runtime"] = True
    except Exception as exc:
        details["mujoco_error_type"] = type(exc).__name__
        checks["mujoco_runtime"] = False

    endpoint = os.getenv("GATEKEEPER_URL", "").strip()
    token_present = bool(os.getenv("GATEKEEPER_TOKEN", "").strip())
    details["gatekeeper"] = {
        "configured": bool(endpoint),
        "endpoint": endpoint if endpoint else None,
        "https": _https_endpoint(endpoint),
        "token_present": token_present,
        "token_value_recorded": False,
    }
    if require_gatekeeper:
        checks["gatekeeper_endpoint_configured"] = bool(endpoint) and _https_endpoint(endpoint)
        checks["gatekeeper_token_present"] = token_present

    tenki_mode = os.getenv("TENKI_MODE", "off").strip().lower()
    tenki_endpoint = os.getenv("TENKI_DERIVE_URL", "").strip()
    tenki_token_present = bool(os.getenv("TENKI_DERIVE_TOKEN", "").strip())
    details["tenki"] = {
        "mode": tenki_mode,
        "configured": bool(tenki_endpoint),
        "endpoint": tenki_endpoint if tenki_endpoint else None,
        "https_derive": _tenki_endpoint(tenki_endpoint),
        "derive_token_present": tenki_token_present,
        "token_value_recorded": False,
        "authority": False,
    }
    if require_tenki:
        checks["tenki_mode_enabled"] = tenki_mode in {"observe", "required"}
        checks["tenki_endpoint_configured"] = _tenki_endpoint(tenki_endpoint)

    if camera_index is not None:
        if type(camera_index) is not int or camera_index < 0:
            raise ValueError("camera_index must be a non-negative integer")
        try:
            cv2 = importlib.import_module("cv2")
            camera = cv2.VideoCapture(camera_index)
            try:
                opened = bool(camera.isOpened())
                ok, frame = camera.read() if opened else (False, None)
                checks["camera_opened"] = opened
                checks["camera_frame_received"] = bool(ok and frame is not None and getattr(frame, "size", 0) > 0)
                if checks["camera_frame_received"]:
                    details["camera_frame_shape"] = [int(value) for value in frame.shape]
            finally:
                camera.release()
        except Exception as exc:
            details["camera_error_type"] = type(exc).__name__
            checks["camera_opened"] = False
            checks["camera_frame_received"] = False

    required = [
        "git_repository",
        "clean_worktree",
        "openvino_installed",
        "mujoco_installed",
        "opencv_installed",
        "openvino_runtime",
        "mujoco_runtime",
    ]
    if require_anomalib:
        required.append("anomalib_installed")
    if require_lerobot:
        required.append("lerobot_installed")
    if require_gatekeeper:
        required.extend(("gatekeeper_endpoint_configured", "gatekeeper_token_present"))
    if require_tenki:
        required.extend(("tenki_mode_enabled", "tenki_endpoint_configured"))
    if camera_index is not None:
        required.extend(("camera_opened", "camera_frame_received"))

    return {
        "schema": "oasse.onsite-preflight.v1",
        "checked_at_ms": int(time.time() * 1000),
        "non_actuating": True,
        "passed": all(checks.get(name) is True for name in required),
        "required_checks": required,
        "checks": checks,
        "details": details,
    }


def verify_acceptance(record: dict[str, Any], *, current_commit: str | None = None) -> dict[str, Any]:
    """Validate the operator record structurally; this is not certification."""
    errors: list[str] = []
    if record.get("record_type") != "operator-attestation-not-certification":
        errors.append("record_type")
    operator = record.get("operator")
    if not isinstance(operator, str) or not operator.strip():
        errors.append("operator")
    commit = record.get("verified_commit")
    if not isinstance(commit, str) or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit.lower()):
        errors.append("verified_commit")
    elif current_commit is not None and commit != current_commit:
        errors.append("verified_commit_mismatch")
    for field in REQUIRED_ACCEPTANCE_FIELDS:
        if type(record.get(field)) is not bool:
            errors.append(field + "_not_boolean")
    notes = record.get("evidence_notes")
    if not isinstance(notes, dict):
        errors.append("evidence_notes")
    false_fields = [field for field in REQUIRED_ACCEPTANCE_FIELDS if record.get(field) is not True]
    return {
        "schema": "oasse.onsite-acceptance-validation.v1",
        "structurally_valid": not errors,
        "all_acceptance_checks_true": not false_fields,
        "passed": not errors and not false_fields,
        "errors": errors,
        "remaining": false_fields,
        "record_type": record.get("record_type"),
        "verified_commit": commit,
    }


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON document must be an object")
    return value
