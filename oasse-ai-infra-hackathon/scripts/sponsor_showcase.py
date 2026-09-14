"""Generate a non-actuating sponsor-stack evidence report for judges and demo recording."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
from pathlib import Path


def version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def build_report() -> dict:
    report = {
        "schema": "oasse.sponsor-runtime-evidence.v1",
        "challenge_sponsor": "Intel",
        "challenge": "Intel Physical AI Challenge",
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "intel_hardware_claimed": False,
        },
        "intel_stack": {
            "openvino": {"version": version("openvino"), "available_devices": [], "selected_device": os.getenv("OPENVINO_DEVICE")},
            "anomalib": {"version": version("anomalib")},
            "physical_ai_studio": {"verified": False},
            "robotics_ai_suite": {"verified": False},
        },
        "planner_runtime": {"lerobot_version": version("lerobot")},
        "physical_hardware_commanded": False,
        "notes": [
            "This report performs no camera or actuator command.",
            "Presence of a package is not evidence that onsite hardware or a trained model was used.",
        ],
    }
    try:
        import openvino as ov
        core = ov.Core()
        report["intel_stack"]["openvino"]["runtime_imported"] = True
        report["intel_stack"]["openvino"]["available_devices"] = list(core.available_devices)
    except Exception as exc:
        report["intel_stack"]["openvino"]["runtime_imported"] = False
        report["intel_stack"]["openvino"]["error_type"] = type(exc).__name__
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    report = build_report()
    encoded = json.dumps(report, indent=2, allow_nan=False)
    print(encoded)
    if args.output:
        Path(args.output).write_text(encoded + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
