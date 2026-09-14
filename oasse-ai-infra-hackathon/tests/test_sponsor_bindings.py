from __future__ import annotations

from oasse_physical_ai.sponsor_bindings import validate_manifest


def test_binding_manifest_resolves_required_python_and_builtin_slots():
    result = validate_manifest(
        {
            "schema": "oasse.sponsor-bindings.v1",
            "sponsor": "Intel",
            "track": "Intel Physical AI Challenge",
            "packages": [],
            "required_before_motion": ["camera", "inference"],
            "slots": {
                "camera": {"mode": "python", "entrypoint": "math:sqrt"},
                "inference": {"mode": "builtin", "component": "NativeOpenVINOPerception"},
                "stop": {"mode": "hardware", "component": "E-stop"},
            },
        }
    )
    assert result["passed"] is True
    assert result["slots"]["camera"]["resolved"] is True
    assert result["slots"]["stop"]["resolved"] is False


def test_binding_manifest_fails_closed_for_unresolved_required_slot():
    result = validate_manifest(
        {
            "schema": "oasse.sponsor-bindings.v1",
            "sponsor": "Intel",
            "track": "Intel Physical AI Challenge",
            "packages": [],
            "required_before_motion": ["actuator"],
            "slots": {
                "actuator": {"mode": "python", "entrypoint": "does_not_exist:execute"}
            },
        }
    )
    assert result["passed"] is False
    assert result["unresolved_required"] == ["actuator"]


def test_hardware_declaration_cannot_satisfy_software_binding():
    result = validate_manifest(
        {
            "schema": "oasse.sponsor-bindings.v1",
            "sponsor": "Intel",
            "track": "Intel Physical AI Challenge",
            "packages": [],
            "required_before_motion": ["stop"],
            "slots": {"stop": {"mode": "hardware", "component": "physical E-stop"}},
        }
    )
    assert result["passed"] is False
    assert result["unresolved_required"] == ["stop"]
