"""Probe the deployed authority contract without moving a robot."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from oasse_physical_ai.live_probe import probe_gatekeeper


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-policy-version", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-loopback-http", action="store_true")
    args = parser.parse_args()
    report = probe_gatekeeper(os.getenv("GATEKEEPER_URL", ""),
        expected_policy_version=args.expected_policy_version, token=os.getenv("GATEKEEPER_TOKEN", ""),
        allow_loopback_http=args.allow_loopback_http)
    Path(args.output).write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print("Gatekeeper contract probe:", "PASS" if report["passed"] else "FAIL", "(no actuator invoked)")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__": main()
