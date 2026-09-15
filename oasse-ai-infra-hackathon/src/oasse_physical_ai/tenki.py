"""Optional Tenki-derived evidence for the pre-authority boundary.

Tenki is a non-authoritative compute plane. It may derive evidence about the
exact evidence/action artifact, but it can never grant execution authority or
modify executable action fields. The default mode is OFF so the existing
Physical AI path is unchanged unless explicitly enabled.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from typing import Any, Protocol
from urllib.parse import urlsplit

import httpx

from .dispatch import snapshot_fields
from .models import EvidenceFrame, ProposedAction
from .normalization import plain

TENKI_REQUEST_SCHEMA = "oasse.tenki-physical-action.v1"
TENKI_RECORD_SCHEMA = "oasse.tenki-derived-evidence.v1"
MAX_TENKI_REQUEST_BYTES = 16 * 1024
MAX_TENKI_RESPONSE_BYTES = 128 * 1024
MAX_TENKI_CLAIM_BYTES = 32 * 1024
MAX_TENKI_CONTROL_TEXT = 256

_FORBIDDEN_AUTHORITY_FIELDS = {
    "authority",
    "permit",
    "capability",
    "token",
    "gatekeeper_verdict",
    "authorized_action",
    "verdict",
}
_HEX64 = re.compile(r"[0-9a-f]{64}")


class TenkiEvidenceError(RuntimeError):
    """Bounded failure code for Tenki-derived evidence."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class PreAuthorityEvidenceProvider(Protocol):
    name: str
    required: bool

    def derive(self, evidence: EvidenceFrame, action: ProposedAction) -> dict[str, Any]: ...
    def close(self) -> None: ...


def _bounded_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_TENKI_CONTROL_TEXT:
        raise TenkiEvidenceError(f"TENKI_{name.upper()}_INVALID")
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _base_action_snapshot(action: ProposedAction) -> dict[str, Any]:
    snapshot = snapshot_fields(action)
    metadata = dict(snapshot.get("metadata", {}))
    # This field is reserved for the trusted pre-authority adapter. Excluding it
    # makes artifact identity stable if an already-enriched action is inspected.
    metadata.pop("pre_authority_evidence", None)
    snapshot["metadata"] = metadata
    return snapshot


def build_artifact(evidence: EvidenceFrame, action: ProposedAction) -> dict[str, Any]:
    evidence_snapshot = snapshot_fields(evidence)
    action_snapshot = _base_action_snapshot(action)
    payload = {
        "schema": TENKI_REQUEST_SCHEMA,
        "evidence": evidence_snapshot,
        "action": action_snapshot,
    }
    canonical = _canonical(payload)
    digest = hashlib.sha256(b"OASSE-PHYSICAL-AI-TENKI-v1\0" + canonical).hexdigest()
    evidence_sha = hashlib.sha256(_canonical(evidence_snapshot)).hexdigest()
    action_sha = hashlib.sha256(_canonical(action_snapshot)).hexdigest()
    return {
        "artifact_ref": f"sha256:{digest}",
        "artifact_sha256": digest,
        "evidence_sha256": evidence_sha,
        "action_sha256": action_sha,
    }


def requested_effect(action: ProposedAction) -> str:
    value = f"physical-ai.execute:{action.action_type}:{action.object_id}:{action.target_bin}"
    return _bounded_text(value, "requested_effect")


def _validate_derive_url(value: str, *, allow_loopback_http: bool = False) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError("TENKI_DERIVE_URL is required when Tenki is enabled")
    if any(ord(char) < 33 for char in value):
        raise ValueError("TENKI_DERIVE_URL contains whitespace or control characters")
    parsed = urlsplit(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname:
        raise ValueError("TENKI_DERIVE_URL must not contain credentials, query, or fragment")
    loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not (allow_loopback_http and loopback and parsed.scheme == "http"):
        raise ValueError("Tenki derive requires HTTPS except explicitly enabled loopback HTTP")
    if not parsed.path.rstrip("/").endswith("/derive"):
        raise ValueError("TENKI_DERIVE_URL must identify the /derive endpoint")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("TENKI_DERIVE_URL has an invalid port") from exc
    return value.rstrip("/")


def _assert_non_authoritative(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in _FORBIDDEN_AUTHORITY_FIELDS:
                if key == "authority":
                    if child is not False:
                        raise TenkiEvidenceError("TENKI_AUTHORITY_ASSERTION")
                elif child not in (None, False):
                    raise TenkiEvidenceError("TENKI_AUTHORITY_ASSERTION")
            _assert_non_authoritative(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_non_authoritative(child, f"{path}[{index}]")


def _validate_claim(payload: Any, *, artifact: dict[str, Any], effect: str,
                    principal: str, secret: str = "") -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise TenkiEvidenceError("TENKI_RESPONSE_INVALID")
    claim_raw = payload.get("claim")
    if not isinstance(claim_raw, dict):
        raise TenkiEvidenceError("TENKI_RESPONSE_INVALID")
    try:
        claim = plain(claim_raw, max_depth=12, max_nodes=2048)
        encoded = _canonical(claim)
    except Exception as exc:
        raise TenkiEvidenceError("TENKI_RESPONSE_INVALID") from exc
    if len(encoded) > MAX_TENKI_CLAIM_BYTES:
        raise TenkiEvidenceError("TENKI_CLAIM_TOO_LARGE")
    _assert_non_authoritative(claim)
    if claim.get("authority") is not False:
        raise TenkiEvidenceError("TENKI_AUTHORITY_ASSERTION")
    expected = {
        "artifact_ref": artifact["artifact_ref"],
        "artifact_sha256": artifact["artifact_sha256"],
        "requested_effect": effect,
        "principal": principal,
        "compute_plane": "tenki",
        "role": "derived_claim_only",
    }
    for key, value in expected.items():
        if claim.get(key) != value:
            raise TenkiEvidenceError("TENKI_BINDING_MISMATCH")
    claim_hash = claim.get("claim_hash")
    if not isinstance(claim_hash, str) or _HEX64.fullmatch(claim_hash) is None:
        raise TenkiEvidenceError("TENKI_CLAIM_HASH_INVALID")
    if secret and secret.encode("utf-8") in encoded:
        raise TenkiEvidenceError("TENKI_CREDENTIAL_ECHO")
    return claim


class TenkiDerivedEvidenceClient:
    """Pooled, bounded client for the verified Tenki ``POST /derive`` contract."""

    name = "tenki"

    def __init__(self, derive_url: str, *, timeout_s: float = 0.20,
                 required: bool = False, token: str = "",
                 transport: httpx.BaseTransport | None = None,
                 allow_loopback_http: bool = False) -> None:
        if not isinstance(timeout_s, (int, float)) or isinstance(timeout_s, bool) or not 0 < float(timeout_s) <= 5:
            raise ValueError("Tenki timeout must be in (0, 5] seconds")
        if not isinstance(token, str):
            raise TypeError("Tenki derive token must be a string")
        self.derive_url = _validate_derive_url(derive_url, allow_loopback_http=allow_loopback_http)
        self.timeout_s = float(timeout_s)
        self.required = bool(required)
        self.token = token
        self._transport = transport
        self._client: httpx.Client | None = None
        self._closed = False
        self._lock = threading.RLock()

    def _get_client(self) -> httpx.Client:
        with self._lock:
            if self._closed:
                raise TenkiEvidenceError("TENKI_CLIENT_CLOSED")
            if self._client is None:
                headers = {"Content-Type": "application/json", "Accept": "application/json"}
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"
                self._client = httpx.Client(
                    timeout=self.timeout_s,
                    transport=self._transport,
                    headers=headers,
                    limits=httpx.Limits(max_connections=4, max_keepalive_connections=2,
                                        keepalive_expiry=30.0),
                )
            return self._client

    def close(self) -> None:
        with self._lock:
            self._closed = True
            client, self._client = self._client, None
        if client is not None and not client.is_closed:
            client.close()

    def derive(self, evidence: EvidenceFrame, action: ProposedAction) -> dict[str, Any]:
        started = time.perf_counter_ns()
        artifact = build_artifact(evidence, action)
        effect = requested_effect(action)
        principal = _bounded_text(action.actor_id, "principal")
        request = {
            "artifact_ref": artifact["artifact_ref"],
            "artifact_sha256": artifact["artifact_sha256"],
            "requested_effect": effect,
            "principal": principal,
        }
        body = _canonical(request)
        if len(body) > MAX_TENKI_REQUEST_BYTES:
            raise TenkiEvidenceError("TENKI_REQUEST_TOO_LARGE")

        try:
            raw = bytearray()
            with self._get_client().stream("POST", self.derive_url, content=body) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    if len(raw) + len(chunk) > MAX_TENKI_RESPONSE_BYTES:
                        raise TenkiEvidenceError("TENKI_RESPONSE_TOO_LARGE")
                    raw.extend(chunk)
        except TenkiEvidenceError:
            raise
        except Exception as exc:
            raise TenkiEvidenceError("TENKI_UNAVAILABLE") from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise TenkiEvidenceError("TENKI_RESPONSE_INVALID") from exc
        claim = _validate_claim(payload, artifact=artifact, effect=effect,
                                principal=principal, secret=self.token)
        elapsed_ms = (time.perf_counter_ns() - started) / 1e6
        return {
            "schema": TENKI_RECORD_SCHEMA,
            "provider": "tenki",
            "status": "LIVE",
            "authority": False,
            "required": self.required,
            **artifact,
            "requested_effect": effect,
            "principal": principal,
            "claim_hash": claim["claim_hash"],
            "compute_plane": "tenki",
            "role": "derived_claim_only",
            "elapsed_ms": elapsed_ms,
            "claim": claim,
        }


def configured_tenki_mode() -> str:
    mode = os.getenv("TENKI_MODE", "off").strip().lower()
    if mode not in {"off", "observe", "required"}:
        raise ValueError("TENKI_MODE must be off, observe, or required")
    return mode


def build_tenki_provider() -> TenkiDerivedEvidenceClient | None:
    mode = configured_tenki_mode()
    if mode == "off":
        return None
    allow_loopback = os.getenv("TENKI_ALLOW_LOOPBACK_HTTP", "0").strip() == "1"
    return TenkiDerivedEvidenceClient(
        os.getenv("TENKI_DERIVE_URL", "").strip(),
        timeout_s=float(os.getenv("TENKI_TIMEOUT_S", "0.20")),
        required=mode == "required",
        token=os.getenv("TENKI_DERIVE_TOKEN", ""),
        allow_loopback_http=allow_loopback,
    )
