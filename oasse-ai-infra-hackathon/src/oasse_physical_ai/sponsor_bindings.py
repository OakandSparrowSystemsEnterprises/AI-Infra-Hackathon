"""Non-actuating sponsor binding manifest validation."""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
from typing import Any

from .providers.sponsor_bridge import resolve_callable

MANIFEST_SCHEMA = "oasse.sponsor-bindings.v1"


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def validate_manifest(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if value.get("schema") != MANIFEST_SCHEMA:
        errors.append("schema")

    sponsor = value.get("sponsor")
    track = value.get("track")
    if not isinstance(sponsor, str) or not sponsor.strip():
        errors.append("sponsor")
    if not isinstance(track, str) or not track.strip():
        errors.append("track")

    packages = value.get("packages", [])
    package_results: dict[str, str | None] = {}
    if not isinstance(packages, list) or any(
        not isinstance(item, str) or not item for item in packages
    ):
        errors.append("packages")
        packages = []
    for name in packages:
        package_results[name] = package_version(name)

    slots = value.get("slots")
    slot_results: dict[str, dict[str, Any]] = {}
    if not isinstance(slots, dict):
        errors.append("slots")
        slots = {}

    required_slots = value.get("required_before_motion", [])
    if not isinstance(required_slots, list) or any(
        not isinstance(item, str) or not item for item in required_slots
    ):
        errors.append("required_before_motion")
        required_slots = []

    for name, config in slots.items():
        if not isinstance(name, str) or not name or not isinstance(config, dict):
            errors.append(f"slot:{name}")
            continue
        mode = config.get("mode", "python")
        result: dict[str, Any] = {"declared": True, "resolved": False, "mode": mode}
        if mode == "python":
            entrypoint = config.get("entrypoint")
            result["entrypoint"] = entrypoint
            try:
                resolve_callable(entrypoint)
                result["resolved"] = True
            except Exception as exc:
                result["error_type"] = type(exc).__name__
        elif mode == "builtin":
            component = config.get("component")
            result["component"] = component
            result["resolved"] = isinstance(component, str) and bool(component.strip())
        elif mode == "hardware":
            result["component"] = config.get("component")
            # Physical stop/E-stop declarations are recorded but are never
            # converted into a software-ready result by this validator.
            result["resolved"] = False
        else:
            result["error_type"] = "UnsupportedMode"
        slot_results[name] = result

    unresolved_required = [
        name
        for name in required_slots
        if name not in slot_results or slot_results[name].get("resolved") is not True
    ]
    missing_packages = [
        name for name, version in package_results.items() if version is None
    ]
    return {
        "schema": "oasse.sponsor-binding-validation.v1",
        "non_actuating": True,
        "sponsor": sponsor,
        "track": track,
        "structurally_valid": not errors,
        "packages": package_results,
        "slots": slot_results,
        "required_before_motion": required_slots,
        "unresolved_required": unresolved_required,
        "missing_packages": missing_packages,
        "passed": not errors and not unresolved_required and not missing_packages,
        "errors": errors,
    }


def load_manifest(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("binding manifest must be a JSON object")
    return value
