from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Dict, List


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    frac = k - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac


@dataclass
class Metrics:
    authority_latencies_ms: List[float] = field(default_factory=list)
    total_latencies_ms: List[float] = field(default_factory=list)
    verdict_counts: Dict[str, int] = field(default_factory=dict)

    def record(self, verdict: str, authority_ms: float, total_ms: float) -> None:
        self.authority_latencies_ms.append(authority_ms)
        self.total_latencies_ms.append(total_ms)
        self.verdict_counts[verdict] = self.verdict_counts.get(verdict, 0) + 1

    def snapshot(self) -> Dict[str, object]:
        return {
            "runs": len(self.total_latencies_ms),
            "verdict_counts": dict(self.verdict_counts),
            "authority_p50_ms": percentile(self.authority_latencies_ms, 0.50),
            "authority_p95_ms": percentile(self.authority_latencies_ms, 0.95),
            "total_p50_ms": percentile(self.total_latencies_ms, 0.50),
            "total_p95_ms": percentile(self.total_latencies_ms, 0.95),
        }
