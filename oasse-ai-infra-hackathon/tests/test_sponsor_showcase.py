import json
from pathlib import Path

from oasse_physical_ai import __version__ as _package_version  # noqa: F401


def test_sponsor_manifest_is_intel_first_and_claim_bounded():
    app = Path(__file__).parents[1]
    data = json.loads((app / "config/sponsor-showcase.json").read_text(encoding="utf-8"))
    assert data["schema"] == "oasse.sponsor-showcase.v1"
    assert data["challenge_sponsor"]["name"] == "Intel"
    assert data["challenge_sponsor"]["challenge"] == "Intel Physical AI Challenge"
    components = {item["component"]: item for item in data["intel_showcase"]}
    assert "OpenVINO" in components
    assert "Anomalib" in components
    assert "Physical AI Studio" in components
    assert "Robotics AI Suite" in components
    assert "verified" in components["OpenVINO"]["claim_state"]
    assert "onsite target" in components["Anomalib"]["claim_state"]


def test_runtime_report_never_claims_hardware_or_motion_by_default():
    from importlib.util import module_from_spec, spec_from_file_location
    script = Path(__file__).parents[1] / "scripts/sponsor_showcase.py"
    spec = spec_from_file_location("sponsor_showcase", script)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    report = module.build_report()
    assert report["challenge_sponsor"] == "Intel"
    assert report["physical_hardware_commanded"] is False
    assert report["host"]["intel_hardware_claimed"] is False
    assert "openvino" in report["intel_stack"]
