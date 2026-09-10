#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.scenarios import SCENARIOS


def main() -> int:
    orch = PhysicalAIOrchestrator()
    print("Gatekeeper: Pre-Execution Security for Physical AI")
    print("=" * 58)
    for name, description in SCENARIOS.items():
        result = orch.run(name)
        print(f"{name:18} {result.decision.verdict.value:10} executed={str(result.executed):5} authority_ms={result.decision.authority_latency_ms:.3f}  {description}")
    print("\nReceipt chain valid:", orch.receipts.verify(), "receipts:", len(orch.receipts.all()))
    print("Metrics:", json.dumps(orch.metrics.snapshot(), indent=2))
    return 0 if orch.receipts.verify() else 2


if __name__ == "__main__":
    raise SystemExit(main())
