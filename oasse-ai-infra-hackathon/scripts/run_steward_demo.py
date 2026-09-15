from __future__ import annotations

import json

from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.steward import build_greenfield_steward_from_env


def main() -> None:
    steward = build_greenfield_steward_from_env()
    orchestrator = PhysicalAIOrchestrator(pre_authority=steward)
    try:
        print("Gatekeeper + Greenfield Steward + Physical AI")
        print("=" * 58)
        for scenario in ("allow", "defect", "overspeed", "stale"):
            result = orchestrator.run(scenario)
            record = result.decision.original_action.metadata.get("pre_authority_evidence", {}).get("steward")
            print(
                f"{scenario:10s} verdict={result.decision.verdict.value:9s} "
                f"executed={str(result.executed):5s} "
                f"steward={record.get('status') if isinstance(record, dict) else 'NONE'}"
            )
        print(json.dumps({
            "receipt_chain_valid": orchestrator.receipts.verify(),
            "receipt_count": len(orchestrator.receipts.all()),
            "metrics": orchestrator.metrics.snapshot(),
        }, indent=2, sort_keys=True))
    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
