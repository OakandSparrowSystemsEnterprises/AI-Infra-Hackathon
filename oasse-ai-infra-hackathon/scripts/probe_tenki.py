"""Non-actuating Tenki /derive contract probe."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from oasse_physical_ai.models import EvidenceFrame, ProposedAction
from oasse_physical_ai.tenki import TenkiDerivedEvidenceClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--url", default=os.getenv("TENKI_DERIVE_URL", ""))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("TENKI_TIMEOUT_S", "0.20")))
    args = parser.parse_args()

    evidence = EvidenceFrame.fresh(
        evidence_id="tenki-probe-evidence",
        frame_hash="tenki-probe-frame-not-a-camera-capture",
        scene_hash="tenki-probe-scene",
        metadata={"provider": "tenki-contract-probe", "physical_observation": False},
    )
    action = ProposedAction.pick_place(
        evidence.evidence_id,
        action_id="tenki-probe-action",
        actor_id="vla-planner-1",
        target_bin="accept",
        speed_mps=0.0,
        trajectory=[[0.0, 0.0, 0.0]],
        metadata={"probe_only": True, "physical_execution": False},
    )
    client = TenkiDerivedEvidenceClient(
        args.url,
        timeout_s=args.timeout,
        required=True,
        token=os.getenv("TENKI_DERIVE_TOKEN", ""),
        allow_loopback_http=os.getenv("TENKI_ALLOW_LOOPBACK_HTTP", "0") == "1",
    )
    try:
        record = client.derive(evidence, action)
    finally:
        client.close()
    result = {
        "schema": "oasse.tenki-probe.v1",
        "non_actuating": True,
        "physical_hardware_commanded": False,
        "passed": record.get("status") == "LIVE" and record.get("authority") is False,
        "record": record,
    }
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
