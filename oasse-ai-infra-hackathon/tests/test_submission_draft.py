from copy import deepcopy

from oasse_physical_ai import __version__

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "check_submission_draft.py"
spec = importlib.util.spec_from_file_location("submission_check", SCRIPT)
submission_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submission_check)


def test_manifest_is_valid_draft():
    data = submission_check.load()
    assert submission_check.validate(data) == []


def test_greenfield_and_mit_are_required():
    data = submission_check.load()
    bad = deepcopy(data)
    bad["greenfield"] = False
    assert any("greenfield" in error for error in submission_check.validate(bad))
    bad = deepcopy(data)
    bad["license"] = "Proprietary"
    assert any("MIT" in error for error in submission_check.validate(bad))


def test_final_commit_requires_full_sha():
    data = submission_check.load()
    bad = deepcopy(data)
    bad["submission_fields"]["final_commit"] = "abc123"
    assert any("40-character" in error for error in submission_check.validate(bad))


def test_package_version_available():
    assert isinstance(__version__, str) and __version__
