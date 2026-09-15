from __future__ import annotations

import argparse
import json
from pathlib import Path

from oasse_physical_ai.models import EvidenceFrame, ProposedAction
from oasse_physical_ai.steward import build_greenfield_steward_from_env


def main() -> None:
    parser = argparse.ArgumentParser(description="Non-actuating Greenfield Steward probe")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    evidence = EvidenceFrame.fresh(
        frame_hash="steward-probe-frame",
        scene_hash="steward-probe-scene",
        confidence=1.0,
        workspace_clear=True,
    )
    action = ProposedAction.pick_place(evidence.evidence_id, speed_mps=0.2)
    steward = build_greenfield_steward_from_env()
    try:
        record = steward.derive(evidence, action)
    finally:
        steward.close()

    text = json.dumps(record, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
