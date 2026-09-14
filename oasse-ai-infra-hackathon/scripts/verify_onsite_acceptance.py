"""Validate an operator acceptance record against the current commit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from oasse_physical_ai.onsite import load_json, verify_acceptance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("record")
    parser.add_argument("--output")
    args = parser.parse_args()
    app = Path(__file__).resolve().parents[1]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=app, text=True).strip()
    report = verify_acceptance(load_json(Path(args.record)), current_commit=commit)
    encoded = json.dumps(report, indent=2, allow_nan=False)
    print(encoded)
    if args.output:
        Path(args.output).write_text(encoded + "\n", encoding="utf-8")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
