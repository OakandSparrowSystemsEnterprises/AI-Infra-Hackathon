from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from types import SimpleNamespace

from oasse_physical_ai.models import EvidenceFrame, ProposedAction
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine
from oasse_physical_ai.providers.so101 import SO101Actuator, connect_event_so101


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DENY/ALLOW proof on a calibrated SO-101 follower.")
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--robot-id", default="hack_follower")
    parser.add_argument("--target-pan", type=float, required=True)
    parser.add_argument("--max-delta-deg", type=float, default=60.0)
    parser.add_argument("--output", default="onsite/so101-governed-proof.json")
    parser.add_argument("--execute", action="store_true", help="Required because the ALLOW phase physically moves the arm.")
    args = parser.parse_args()

    if not args.execute:
        raise SystemExit("Refusing physical motion without --execute")
    if not 0 < args.max_delta_deg <= 90:
        raise SystemExit("--max-delta-deg must be in (0, 90]")

    robot = connect_event_so101(port=args.port, calibration_id=args.robot_id, calibrate=False)
    try:
        start = dict(robot.get_observation())
        current_pan = float(start["shoulder_pan.pos"])
        if abs(args.target_pan - current_pan) > args.max_delta_deg:
            raise SystemExit(
                f"Refusing {abs(args.target_pan-current_pan):.2f} degree pan delta; "
                f"limit is {args.max_delta_deg:.2f}"
            )

        target = dict(start)
        target["shoulder_pan.pos"] = float(args.target_pan)

        vla = SimpleNamespace(
            propose=lambda evidence, scenario="allow": ProposedAction.pick_place(
                evidence.evidence_id,
                speed_mps=0.05,
                metadata={
                    "planner": "onsite-so101-governed-demo",
                    "joint_action": dict(target),
                },
            )
        )
        actuator = SO101Actuator(robot)
        authority = ReferenceAuthorityEngine(evidence_max_age_ms=5000)
        orch = PhysicalAIOrchestrator(authority=authority, vla=vla, actuator=actuator)

        orch.perception = SimpleNamespace(
            observe=lambda scenario="allow": EvidenceFrame.fresh(
                confidence=0.99,
                workspace_clear=False,
                metadata={"provider": "onsite-proof", "case": "deny"},
            )
        )
        deny_before = dict(robot.get_observation())
        deny_result = orch.run()
        deny_after = dict(robot.get_observation())

        orch.perception = SimpleNamespace(
            observe=lambda scenario="allow": EvidenceFrame.fresh(
                confidence=0.99,
                workspace_clear=True,
                metadata={"provider": "onsite-proof", "case": "allow"},
            )
        )
        allow_before = dict(robot.get_observation())
        allow_result = orch.run()
        time.sleep(1.0)
        allow_after = dict(robot.get_observation())

        proof = {
            "schema": "oasse.so101-governed-proof.v1",
            "robot": {"port": args.port, "id": args.robot_id},
            "target_joint_action": target,
            "deny": {
                "before": deny_before,
                "after": deny_after,
                "result": deny_result.to_dict(),
            },
            "allow": {
                "before": allow_before,
                "after": allow_after,
                "result": allow_result.to_dict(),
            },
            "receipt_chain_valid": orch.receipts.assert_intact(),
        }

        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n", encoding="utf-8")

        summary = {
            "deny_verdict": deny_result.decision.verdict.value,
            "deny_dispatch_attempted": deny_result.dispatch_attempted,
            "deny_executed": deny_result.executed,
            "deny_pan_before": deny_before["shoulder_pan.pos"],
            "deny_pan_after": deny_after["shoulder_pan.pos"],
            "allow_verdict": allow_result.decision.verdict.value,
            "allow_dispatch_attempted": allow_result.dispatch_attempted,
            "allow_executed": allow_result.executed,
            "allow_pan_before": allow_before["shoulder_pan.pos"],
            "allow_pan_after": allow_after["shoulder_pan.pos"],
            "receipt_chain_valid": proof["receipt_chain_valid"],
            "output": str(output),
        }
        print(json.dumps(summary, indent=2))
        return 0 if (
            deny_result.decision.verdict.value == "DENY"
            and not deny_result.dispatch_attempted
            and not deny_result.executed
            and allow_result.decision.verdict.value == "ALLOW"
            and allow_result.dispatch_attempted
            and allow_result.executed
            and proof["receipt_chain_valid"]
        ) else 1
    finally:
        robot.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
