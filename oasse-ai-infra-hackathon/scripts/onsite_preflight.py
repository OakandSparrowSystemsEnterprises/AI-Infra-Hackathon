"""One-command non-actuating onsite machine preflight."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from oasse_physical_ai.onsite import run_preflight


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--camera-index", type=int)
    parser.add_argument("--require-gatekeeper", action="store_true")
    parser.add_argument("--require-anomalib", action="store_true")
    parser.add_argument("--require-lerobot", action="store_true")
    parser.add_argument("--require-tenki", action="store_true")
    args = parser.parse_args()
    app = Path(__file__).resolve().parents[1]
    report = run_preflight(
        app,
        require_gatekeeper=args.require_gatekeeper,
        require_anomalib=args.require_anomalib,
        require_lerobot=args.require_lerobot,
        require_tenki=args.require_tenki,
        camera_index=args.camera_index,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "required_checks": report["required_checks"], "output": str(output)}, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
