"""Append-only receipt chain with isolated public snapshots and O(1) hot-path integrity checks."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import threading
import time
import uuid
from typing import Any, Dict, List

from .models import Receipt
from .normalization import plain, text


def _canonical_plain(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_json(payload: Dict[str, Any]) -> bytes:
    return _canonical_plain(plain(payload))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class _StoredReceipt:
    receipt_id: str
    receipt_type: str
    created_at_ms: int
    payload_hash: str
    prev_hash: str
    receipt_hash: str
    payload_json: bytes


class ReceiptChain:
    """Private immutable records; public callers receive detached snapshots.

    ``assert_intact`` is the constant-time execution gate. Full ``verify`` is
    retained for exported evidence, health checks and explicit review. Hashes
    provide integrity only; they are not signatures or source authentication.
    """

    def __init__(self) -> None:
        self._receipts: List[_StoredReceipt] = []
        self._head = "GENESIS"
        self._healthy = True
        self._lock = threading.RLock()

    @staticmethod
    def _envelope(record: _StoredReceipt) -> dict[str, Any]:
        return {"receipt_id": record.receipt_id, "receipt_type": record.receipt_type,
                "created_at_ms": record.created_at_ms, "payload_hash": record.payload_hash,
                "prev_hash": record.prev_hash}

    @staticmethod
    def _materialize(record: _StoredReceipt) -> Receipt:
        return Receipt(receipt_id=record.receipt_id, receipt_type=record.receipt_type,
                       created_at_ms=record.created_at_ms, payload_hash=record.payload_hash,
                       prev_hash=record.prev_hash, receipt_hash=record.receipt_hash,
                       payload=json.loads(record.payload_json.decode("utf-8")))

    def _tail_valid_locked(self) -> bool:
        if not self._healthy:
            return False
        if not self._receipts:
            return self._head == "GENESIS"
        record = self._receipts[-1]
        expected_prev = "GENESIS" if len(self._receipts) == 1 else self._receipts[-2].receipt_hash
        if record.prev_hash != expected_prev or self._head != record.receipt_hash:
            return False
        if sha256_hex(record.payload_json) != record.payload_hash:
            return False
        return sha256_hex(_canonical_plain(self._envelope(record))) == record.receipt_hash

    @property
    def head(self) -> str:
        with self._lock:
            return self._head

    def assert_intact(self) -> bool:
        with self._lock:
            if not self._tail_valid_locked():
                self._healthy = False
            return self._healthy

    def seal(self, receipt_type: str, payload: Dict[str, Any]) -> Receipt:
        text(receipt_type, "receipt_type")
        if not isinstance(payload, dict):
            raise TypeError("receipt payload must be an object")
        # ``plain`` builds the detached public snapshot once. Internal chain
        # state stores only its canonical bytes, so returning ``snapshot`` here
        # does not create an alias into the chain and avoids a JSON decode.
        snapshot = plain(payload)
        payload_json = _canonical_plain(snapshot)
        payload_hash = sha256_hex(payload_json)
        with self._lock:
            if not self._tail_valid_locked():
                self._healthy = False
                raise RuntimeError("RECEIPT_CHAIN_INVALID")
            created = int(time.time() * 1000)
            record = _StoredReceipt(f"rcpt-{uuid.uuid4().hex[:12]}", receipt_type, created,
                                    payload_hash, self._head, "", payload_json)
            receipt_hash = sha256_hex(_canonical_plain(self._envelope(record)))
            record = _StoredReceipt(record.receipt_id, record.receipt_type, record.created_at_ms,
                                    record.payload_hash, record.prev_hash, receipt_hash,
                                    record.payload_json)
            self._receipts.append(record)
            self._head = receipt_hash
            return Receipt(record.receipt_id, record.receipt_type, record.created_at_ms,
                           record.payload_hash, record.prev_hash, record.receipt_hash, snapshot)

    def all(self) -> List[Receipt]:
        with self._lock:
            return [self._materialize(record) for record in self._receipts]

    def verify(self) -> bool:
        with self._lock:
            if not self._healthy:
                return False
            try:
                previous = "GENESIS"
                for record in self._receipts:
                    if record.prev_hash != previous:
                        self._healthy = False; return False
                    if sha256_hex(record.payload_json) != record.payload_hash:
                        self._healthy = False; return False
                    if sha256_hex(_canonical_plain(self._envelope(record))) != record.receipt_hash:
                        self._healthy = False; return False
                    parsed = json.loads(record.payload_json.decode("utf-8"))
                    if not isinstance(parsed, dict):
                        self._healthy = False; return False
                    previous = record.receipt_hash
                if previous != self._head:
                    self._healthy = False; return False
                return True
            except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError):
                self._healthy = False
                return False
