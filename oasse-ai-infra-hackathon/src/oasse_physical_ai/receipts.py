"""Strict JSON receipt snapshots with serialized in-process chain appends."""
from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from typing import Any, Dict, List

from .models import Receipt
from .normalization import plain, text


def canonical_json(payload: Dict[str, Any]) -> bytes:
    return json.dumps(plain(payload), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ReceiptChain:
    def __init__(self) -> None:
        self._receipts: List[Receipt] = []
        self._lock = threading.RLock()

    @property
    def head(self) -> str:
        with self._lock:
            return self._receipts[-1].receipt_hash if self._receipts else "GENESIS"

    def seal(self, receipt_type: str, payload: Dict[str, Any]) -> Receipt:
        text(receipt_type, "receipt_type")
        if not isinstance(payload, dict):
            raise TypeError("receipt payload must be an object")
        snapshot = plain(payload)
        encoded = canonical_json(snapshot)
        with self._lock:
            created = int(time.time() * 1000)
            payload_hash = sha256_hex(encoded)
            prev_hash = self.head
            envelope = {"receipt_type": receipt_type, "created_at_ms": created,
                        "payload_hash": payload_hash, "prev_hash": prev_hash}
            receipt = Receipt(receipt_id=f"rcpt-{uuid.uuid4().hex[:12]}", receipt_type=receipt_type,
                              created_at_ms=created, payload_hash=payload_hash, prev_hash=prev_hash,
                              receipt_hash=sha256_hex(canonical_json(envelope)), payload=snapshot)
            self._receipts.append(receipt)
            return receipt

    def all(self) -> List[Receipt]:
        with self._lock:
            return list(self._receipts)

    def verify(self) -> bool:
        with self._lock:
            try:
                prev = "GENESIS"
                for receipt in self._receipts:
                    if receipt.prev_hash != prev:
                        return False
                    if sha256_hex(canonical_json(receipt.payload)) != receipt.payload_hash:
                        return False
                    envelope = {"receipt_type": receipt.receipt_type, "created_at_ms": receipt.created_at_ms,
                                "payload_hash": receipt.payload_hash, "prev_hash": receipt.prev_hash}
                    if sha256_hex(canonical_json(envelope)) != receipt.receipt_hash:
                        return False
                    prev = receipt.receipt_hash
                return True
            except (TypeError, ValueError, OverflowError, RecursionError):
                return False
