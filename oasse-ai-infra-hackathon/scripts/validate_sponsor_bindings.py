"""Resolve onsite sponsor bindings without invoking hardware or models."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from oasse_physical_ai.sponsor_bindings import load_manifest, validate_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--output")
    args = parser.parse_args()

    result = validate_manifest(load_manifest(args.manifest))
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
