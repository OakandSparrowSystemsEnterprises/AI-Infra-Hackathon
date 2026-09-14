from __future__ import annotations

import json
from pathlib import Path

from oasse_physical_ai.onsite import REQUIRED_ACCEPTANCE_FIELDS, verify_acceptance


def complete_record(commit: str = "a" * 40) -> dict:
    record = {
        "record_type": "operator-attestation-not-certification",
        "operator": "onsite-operator",
        "verified_commit": commit,
        "evidence_notes": {},
    }
    record.update({field: True for field in REQUIRED_ACCEPTANCE_FIELDS})
    return record


def test_complete_acceptance_passes_exact_commit():
    record = complete_record()
    report = verify_acceptance(record, current_commit="a" * 40)
    assert report["passed"] is True
    assert report["remaining"] == []


def test_acceptance_is_bound_to_exact_commit():
    report = verify_acceptance(complete_record(), current_commit="b" * 40)
    assert report["passed"] is False
    assert "verified_commit_mismatch" in report["errors"]


def test_false_acceptance_field_remains_visible():
    record = complete_record()
    record["trained_vla"] = False
    report = verify_acceptance(record, current_commit="a" * 40)
    assert report["structurally_valid"] is True
    assert report["passed"] is False
    assert report["remaining"] == ["trained_vla"]


def test_truthy_strings_do_not_count_as_operator_checks():
    record = complete_record()
    record["normal_sort"] = "true"
    report = verify_acceptance(record, current_commit="a" * 40)
    assert report["passed"] is False
    assert "normal_sort_not_boolean" in report["errors"]
    assert "normal_sort" in report["remaining"]


def test_invalid_operator_and_record_type_fail():
    record = complete_record()
    record["operator"] = " "
    record["record_type"] = "certified"
    report = verify_acceptance(record, current_commit="a" * 40)
    assert report["passed"] is False
    assert "operator" in report["errors"]
    assert "record_type" in report["errors"]


def test_example_template_stays_non_claiming():
    path = Path(__file__).parents[1] / "config/onsite-acceptance.example.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["record_type"] == "operator-attestation-not-certification"
    assert all(record[field] is False for field in REQUIRED_ACCEPTANCE_FIELDS)
