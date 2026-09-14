"""Bounded, strict JSON normalization for external adapter values."""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


def plain(value: Any, *, max_depth: int = 32, max_nodes: int = 10000) -> Any:
    """Copy to JSON-native values. Arrays use tolist before scalar item."""
    remaining = max_nodes
    active: set[int] = set()

    def visit(item: Any, depth: int) -> Any:
        nonlocal remaining
        remaining -= 1
        if depth > max_depth or remaining < 0:
            raise ValueError("input exceeds normalization budget")
        if item is None or type(item) in (str, bool, int):
            return item
        if type(item) is float:
            if not math.isfinite(item):
                raise ValueError("non-finite value")
            return item
        identity = id(item)
        if identity in active:
            raise ValueError("cyclic input")
        active.add(identity)
        try:
            if isinstance(item, Mapping):
                if not all(type(key) is str for key in item):
                    raise TypeError("mapping keys must be strings")
                return {key: visit(val, depth + 1) for key, val in item.items()}
            if isinstance(item, (list, tuple)):
                return [visit(val, depth + 1) for val in item]
            # numpy.ndarray has BOTH methods. item() alone fails for vectors.
            if callable(getattr(item, "tolist", None)):
                return visit(item.tolist(), depth + 1)
            if callable(getattr(item, "item", None)):
                return visit(item.item(), depth + 1)
            raise TypeError(f"unsupported value type: {type(item).__name__}")
        finally:
            active.remove(identity)

    return visit(value, 0)


def text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{name} must be a non-empty string")
    return value


def number(value: Any, name: str, *, minimum: float | None = None,
           maximum: float | None = None) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name} must be numeric, not a boolean or string")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} is too large") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} below minimum")
    if maximum is not None and result > maximum:
        raise ValueError(f"{name} above maximum")
    return result


def integer(value: Any, name: str) -> int:
    if type(value) is not int or not 0 <= value <= 2**63 - 1:
        raise TypeError(f"{name} must be a non-negative 64-bit integer")
    return value


def vector(value: Any, name: str, size: int) -> list[float]:
    if not isinstance(value, list) or len(value) != size:
        raise TypeError(f"{name} must contain {size} numbers")
    return [number(item, name) for item in value]


def trajectory(value: Any) -> list[list[float]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 256:
        raise TypeError("trajectory must contain 1 to 256 XYZ points")
    return [vector(point, "trajectory point", 3) for point in value]
