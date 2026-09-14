"""Validate that submission.json remains a complete, honest final-draft manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def load() -> dict:
    return json.loads((APP / "submission.json").read_text(encoding="utf-8"))


def validate(data: dict, *, strict: bool = False) -> list[str]:
    errors: list[str] = []
    required_text = ["name", "team", "challenge", "thesis", "problem", "solution", "novelty", "license"]
    for key in required_text:
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"missing non-empty string: {key}")
    if data.get("license") != "MIT":
        errors.append("submission license must be MIT")
    if data.get("greenfield") is not True:
        errors.append("submission must declare greenfield=true")
    if not isinstance(data.get("architecture"), list) or len(data["architecture"]) < 6:
        errors.append("architecture must contain the complete execution path")
    if not isinstance(data.get("proof_cases"), list) or len(data["proof_cases"]) < 5:
        errors.append("proof_cases must include the core authority demonstrations")
    boundaries = data.get("boundaries")
    if not isinstance(boundaries, dict):
        errors.append("boundaries must be an object")
    fields = data.get("submission_fields")
    if not isinstance(fields, dict):
        errors.append("submission_fields must be an object")
        fields = {}
    final_commit = fields.get("final_commit")
    if final_commit is not None and not (isinstance(final_commit, str) and SHA40.fullmatch(final_commit)):
        errors.append("final_commit must be null or a full 40-character SHA")
    if strict:
        current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        if final_commit != current:
            errors.append("strict mode requires final_commit to equal HEAD")
        for key in ("demo_video_url", "judge_repository_url"):
            if not isinstance(fields.get(key), str) or not fields[key].startswith("https://"):
                errors.append(f"strict mode requires https URL: {key}")
        if data.get("submission_sent") is not True:
            errors.append("strict mode requires submission_sent=true")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Require final URLs, HEAD binding and submitted state")
    args = parser.parse_args()
    data = load()
    errors = validate(data, strict=args.strict)
    if errors:
        for error in errors:
            print("ERROR:", error)
        raise SystemExit(1)
    state = "FINAL" if args.strict else "DRAFT"
    print(f"Submission manifest {state} validation passed")


if __name__ == "__main__":
    main()
