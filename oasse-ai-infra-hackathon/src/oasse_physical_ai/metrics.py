from __future__ import annotations

from collections import deque
from statistics import median
from typing import Dict, Sequence


def percentile(values: Sequence[float], p: float) -> float:
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


class Metrics:
    """Bounded latency window plus lifetime verdict/run counters."""

    def __init__(self, max_samples: int = 4096) -> None:
        if type(max_samples) is not int or not 16 <= max_samples <= 100000:
            raise ValueError("max_samples must be in [16, 100000]")
        self.authority_latencies_ms = deque(maxlen=max_samples)
        self.total_latencies_ms = deque(maxlen=max_samples)
        self.verdict_counts: Dict[str, int] = {}
        self.total_runs = 0

    def record(self, verdict: str, authority_ms: float, total_ms: float) -> None:
        self.authority_latencies_ms.append(authority_ms)
        self.total_latencies_ms.append(total_ms)
        self.verdict_counts[verdict] = self.verdict_counts.get(verdict, 0) + 1
        self.total_runs += 1

    def snapshot(self) -> Dict[str, object]:
        return {
            "runs": self.total_runs,
            "latency_samples": len(self.total_latencies_ms),
            "verdict_counts": dict(self.verdict_counts),
            "authority_p50_ms": percentile(self.authority_latencies_ms, 0.50),
            "authority_p95_ms": percentile(self.authority_latencies_ms, 0.95),
            "total_p50_ms": percentile(self.total_latencies_ms, 0.50),
            "total_p95_ms": percentile(self.total_latencies_ms, 0.95),
        }
