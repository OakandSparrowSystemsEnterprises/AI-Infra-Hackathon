"""Evidence-based submission readiness, separate from software rehearsal success."""
from __future__ import annotations

import importlib.metadata
import importlib.util
import platform
import time
from urllib.parse import urlsplit


def environment_report() -> dict:
    packages = {}
    for name in ("oasse-physical-ai-authority", "openvino", "mujoco", "numpy", "anomalib", "lerobot", "opencv-python-headless"):
        try: packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: packages[name] = None
    return {"python": platform.python_version(), "platform": platform.system(),
            "packages": packages, "hardware_tested": False,
            "native_imports_available": {name: importlib.util.find_spec(name) is not None for name in ("openvino", "mujoco", "cv2")}}


def readiness(rehearsal_passed: bool, *, gatekeeper_probe: dict | None = None,
              onsite_acceptance: dict | None = None) -> dict:
    """An onsite operator record is an attestation, not independent certification."""
    probe = gatekeeper_probe or {}
    onsite = onsite_acceptance or {}
    expected_cases = {"allow", "overspeed", "stale", "occupied", "low_confidence", "binding_mismatch"}
    reports = probe.get("checks", [])
    checked = probe.get("checked_at_ms")
    fresh = type(checked) is int and 0 <= int(time.time()*1000)-checked <= 86400000
    checked_all = (isinstance(reports, list) and len(reports) == len(expected_cases)
                   and all(isinstance(item, dict) and item.get("passed") is True for item in reports)
                   and {item.get("scenario") for item in reports} == expected_cases)
    try:
        url = urlsplit(probe.get("endpoint", ""))
        external_https = url.scheme == "https" and url.hostname not in {None, "127.0.0.1", "localhost", "::1"}
    except (ValueError, TypeError):
        external_https = False
    live = (fresh and checked_all and external_https and probe.get("schema") == "oasse.gatekeeper-probe.v1"
            and probe.get("passed") is True and probe.get("connection_mode") == "http-network"
            and probe.get("receipt_chain_valid") is True
            and probe.get("endpoint_scope") == "configured-service"
            and isinstance(probe.get("expected_policy_version"), str)
            and bool(probe["expected_policy_version"].strip()))
    fields = ("hardware_operator_approval", "camera_calibration", "trained_detector",
              "trained_vla", "pre_send_interception", "normal_sort", "defective_sort",
              "safe_interruption", "video_recorded", "judge_repository_access")
    checks = {"rehearsal": rehearsal_passed is True, "live_authority_contract": live,
              **{field: onsite.get(field) is True for field in fields}}
    return {"rehearsal_ready": checks["rehearsal"], "onsite_submission_ready": all(checks.values()),
            "checks": checks, "remaining": [key for key, value in checks.items() if not value],
            "hardware_status_source": "operator-attestation" if onsite else "not-provided"}
