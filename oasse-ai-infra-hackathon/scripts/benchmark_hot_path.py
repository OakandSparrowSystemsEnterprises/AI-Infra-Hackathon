"""Machine-local regression benchmark for the reference authority hot path.

This is a CI guard against accidental latency regressions, not a hardware or
production-service benchmark. Network, OpenVINO and physical execution are
intentionally excluded from these thresholds.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import time

from oasse_physical_ai.models import EvidenceFrame, ProposedAction
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    index = (len(ordered)-1)*p
    lo = math.floor(index); hi = math.ceil(index)
    if lo == hi: return ordered[lo]
    return ordered[lo]*(hi-index) + ordered[hi]*(index-lo)


def timed(callable_, iterations: int) -> list[float]:
    values = []
    for _ in range(iterations):
        start = time.perf_counter_ns(); callable_(); values.append((time.perf_counter_ns()-start)/1e6)
    return values


def stats(values: list[float]) -> dict[str, float]:
    return {"p50_ms": statistics.median(values), "p95_ms": percentile(values,.95),
            "min_ms": min(values), "max_ms": max(values)}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--iterations",type=int,default=1000)
    parser.add_argument("--max-authority-p95-ms",type=float)
    parser.add_argument("--max-pipeline-p95-ms",type=float)
    args=parser.parse_args()
    if not 100 <= args.iterations <= 10000: raise SystemExit("iterations must be in [100,10000]")

    engine=ReferenceAuthorityEngine()
    evidence=EvidenceFrame.fresh(frame_hash="latency-benchmark")
    action=ProposedAction.pick_place(evidence.evidence_id)
    for _ in range(100): engine.evaluate(evidence,action)
    authority=stats(timed(lambda:engine.evaluate(evidence,action),args.iterations))

    orch=PhysicalAIOrchestrator(authority=ReferenceAuthorityEngine())
    for _ in range(25): orch.run("allow")
    pipeline=stats(timed(lambda:orch.run("allow"),args.iterations))
    assert orch.receipts.assert_intact()

    report={"schema":"oasse.local-hot-path-benchmark.v1","iterations":args.iterations,
            "scope":"machine-local reference authority + synthetic governed dispatch; excludes network/inference/robot",
            "reference_authority":authority,"synthetic_governed_pipeline":pipeline,
            "receipt_count":len(orch.receipts.all())}
    print(json.dumps(report,indent=2))
    if args.max_authority_p95_ms is not None and authority["p95_ms"]>args.max_authority_p95_ms:
        raise SystemExit(f"reference authority p95 {authority['p95_ms']:.3f}ms exceeds budget")
    if args.max_pipeline_p95_ms is not None and pipeline["p95_ms"]>args.max_pipeline_p95_ms:
        raise SystemExit(f"pipeline p95 {pipeline['p95_ms']:.3f}ms exceeds budget")


if __name__=="__main__": main()
