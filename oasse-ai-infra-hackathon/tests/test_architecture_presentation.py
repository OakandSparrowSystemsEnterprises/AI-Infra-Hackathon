from pathlib import Path

APP = Path(__file__).parents[1]
ROOT = APP.parent


def test_root_readme_makes_intel_stack_visible():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for token in ("INTEL", "OPENVINO", "ANOMALIB", "PHYSICAL AI STUDIO", "ROBOTICS AI SUITE"):
        assert token in text.upper()
    assert "SENIOR_ENGINEER_ARCHITECTURE.md" in text


def test_senior_architecture_exposes_real_review_surfaces():
    text = (APP / "docs/SENIOR_ENGINEER_ARCHITECTURE.md").read_text(encoding="utf-8")
    required = (
        "trust boundaries",
        "core data contracts",
        "authority state machine",
        "safety and correctness properties",
        "temporal model",
        "replay and scene-change semantics",
        "failure matrix",
        "receipt model",
        "residual risks and non-claims",
        "senior-review checklist",
    )
    lower = text.lower()
    for heading in required:
        assert heading in lower
    assert "C_I:X_I" in text
    assert "dispatch_attempted" in text
    assert "UNKNOWN" in text


def test_sponsor_document_distinguishes_challenge_from_event_recognition():
    text = (APP / "docs/SPONSOR_SHOWCASE.md").read_text(encoding="utf-8")
    upper = text.upper()
    assert "INTEL" in upper
    assert "AI INFRA SUMMIT 2026" in upper
    for partner in ("AMD", "AWS", "HCLTECH", "ORACLE", "QUALCOMM"):
        assert partner in upper
    assert "EVENT-LEVEL RECOGNITION ONLY" in upper
    assert "DOES NOT IMPLY" in upper
