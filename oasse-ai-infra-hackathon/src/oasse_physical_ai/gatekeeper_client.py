from __future__ import annotations

from dataclasses import fields, replace
import json
import logging
import math
import os
import threading
import time
from typing import Any, Dict, List, Optional, Protocol, Tuple
from urllib.parse import urlsplit

import httpx

from .dispatch import snapshot_fields
from .models import PHYSICAL_ACTION_FIELDS, AuthorityDecision, EvidenceFrame, ProposedAction, Verdict, physically_changed
from .policy import ReferenceAuthorityEngine

log = logging.getLogger(__name__)


class AuthorityClient(Protocol):
    def evaluate(self, evidence: EvidenceFrame, action: ProposedAction) -> AuthorityDecision: ...


class _AuthorityResponseTooLarge(ValueError):
    pass


AUTHORITY_REQUEST_INVALID = "AUTHORITY_REQUEST_INVALID"
AUTHORITY_UNAVAILABLE = "AUTHORITY_UNAVAILABLE"
AUTHORITY_RESPONSE_INVALID = "AUTHORITY_RESPONSE_INVALID"
AUTHORIZED_ACTION_MISSING = "AUTHORIZED_ACTION_MISSING"
AUTHORIZED_ACTION_INVALID = "AUTHORIZED_ACTION_INVALID"
AUTHORIZED_ACTION_UNCHANGED = "AUTHORIZED_ACTION_UNCHANGED"
AUTHORIZED_ACTION_BINDING_MISMATCH = "AUTHORIZED_ACTION_BINDING_MISMATCH"
AUTHORIZED_ACTION_CONFLICT = "AUTHORIZED_ACTION_CONFLICT"

LIVE_POLICY_VERSION_DEFAULT = "gatekeeper-live"
LIVE_UNAVAILABLE_POLICY_VERSION = "gatekeeper-live-unavailable"
MAX_AUTHORITY_REQUEST_BYTES = 1024 * 1024
MAX_AUTHORITY_RESPONSE_BYTES = 1024 * 1024
MAX_REASON_CODES = 64
MAX_CONTROL_TEXT = 256

_BOUND_FIELDS = ("action_id", "actor_id", "evidence_id")
_TEXT_OVERRIDE_FIELDS = frozenset({"action_id", "actor_id", "evidence_id", "action_type", "target_bin", "object_id"})
_ACCEPTED_FIELDS = frozenset(PHYSICAL_ACTION_FIELDS) | frozenset(_BOUND_FIELDS)
assert _ACCEPTED_FIELDS <= {f.name for f in fields(ProposedAction)}


def _is_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _is_text(value: Any, *, maximum: int | None = None) -> bool:
    return (isinstance(value, str) and value.strip() != ""
            and (maximum is None or len(value) <= maximum))


def _validate_base_url(value: str, *, allow_loopback_http: bool = False) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError("Gatekeeper base URL is required without surrounding whitespace")
    if any(ord(char) < 33 for char in value):
        raise ValueError("Gatekeeper base URL contains whitespace or control characters")
    url = urlsplit(value)
    if url.username or url.password or url.query or url.fragment or not url.hostname:
        raise ValueError("Gatekeeper base URL must not contain credentials, query, or fragment")
    loopback = url.hostname in {"127.0.0.1", "localhost", "::1"}
    if url.scheme != "https" and not (allow_loopback_http and loopback and url.scheme == "http"):
        raise ValueError("Gatekeeper requires HTTPS except explicitly enabled loopback HTTP")
    try:
        _ = url.port
    except ValueError as exc:
        raise ValueError("Gatekeeper base URL has an invalid port") from exc
    if url.path.rstrip("/").endswith("/v1/evaluate"):
        raise ValueError("Gatekeeper base URL must not include /v1/evaluate")
    return value.rstrip("/")


def _valid_override(name: str, value: Any) -> bool:
    if name in _TEXT_OVERRIDE_FIELDS:
        return _is_text(value, maximum=MAX_CONTROL_TEXT)
    if name == "speed_mps":
        return _is_number(value) and value >= 0
    if name == "trajectory":
        return (
            isinstance(value, list)
            and 1 <= len(value) <= 256
            and all(isinstance(point, list) and len(point) == 3
                    and all(_is_number(c) for c in point) for point in value)
        )
    return False


def _merge_authorized(original: ProposedAction, raw: Any) -> Tuple[Optional[ProposedAction], Optional[str], bool]:
    if not isinstance(raw, dict):
        return None, AUTHORIZED_ACTION_INVALID, False
    overrides = {key: value for key, value in raw.items() if key in _ACCEPTED_FIELDS}
    if any(not _valid_override(name, value) for name, value in overrides.items()):
        return None, AUTHORIZED_ACTION_INVALID, False
    if "speed_mps" in overrides:
        overrides["speed_mps"] = float(overrides["speed_mps"])
    candidate = replace(original, **overrides)
    if any(getattr(candidate, name) != getattr(original, name) for name in _BOUND_FIELDS):
        return None, AUTHORIZED_ACTION_BINDING_MISMATCH, False
    return candidate, None, physically_changed(candidate, original)


def _parse_response(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("response body must be a JSON object")
    verdict_raw = data.get("verdict")
    if not isinstance(verdict_raw, str):
        raise ValueError("verdict must be a string")
    verdict = Verdict(verdict_raw)
    decision_id = data.get("decision_id")
    if not _is_text(decision_id, maximum=MAX_CONTROL_TEXT):
        raise ValueError("decision_id must be a bounded non-empty string")
    reasons = data.get("reason_codes")
    if reasons is None:
        reasons = []
    if (not isinstance(reasons, list) or len(reasons) > MAX_REASON_CODES
            or not all(_is_text(code, maximum=MAX_CONTROL_TEXT) for code in reasons)):
        raise ValueError("reason_codes must be a bounded list of non-empty strings")
    evaluated_at = data.get("evaluated_at_ms")
    if evaluated_at is None:
        evaluated_at = int(time.time() * 1000)
    if type(evaluated_at) is not int or not 0 <= evaluated_at <= 2**63 - 1:
        raise ValueError("evaluated_at_ms must be a non-negative 64-bit integer")
    latency = data.get("authority_latency_ms")
    if latency is None:
        latency = 0.0
    if not _is_number(latency) or latency < 0:
        raise ValueError("authority_latency_ms must be a non-negative finite number")
    policy_version = data.get("policy_version")
    if policy_version is None:
        policy_version = LIVE_POLICY_VERSION_DEFAULT
    if not _is_text(policy_version, maximum=MAX_CONTROL_TEXT):
        raise ValueError("policy_version must be a bounded non-empty string")
    return {
        "verdict": verdict,
        "decision_id": decision_id,
        "reason_codes": list(reasons),
        "evaluated_at_ms": evaluated_at,
        "authority_latency_ms": float(latency),
        "policy_version": policy_version,
        "authorized_action": data.get("authorized_action"),
    }


def _redact_control_text(parsed: Dict[str, Any], secret: str) -> Dict[str, Any]:
    """Redact only fields that can cross a trusted contract boundary.

    Unknown service fields are intentionally ignored and never traversed.
    """
    if not secret:
        return parsed
    raw_action = parsed.get("authorized_action")
    if isinstance(raw_action, dict):
        for key in _TEXT_OVERRIDE_FIELDS:
            value = raw_action.get(key)
            if isinstance(value, str) and secret in value:
                raise ValueError("authority response echoed credential in executable action data")
    result = dict(parsed)
    result["decision_id"] = result["decision_id"].replace(secret, "[REDACTED]")
    result["policy_version"] = result["policy_version"].replace(secret, "[REDACTED]")
    result["reason_codes"] = [code.replace(secret, "[REDACTED]") for code in result["reason_codes"]]
    return result


class GatekeeperClient:
    """Pooled, bounded and fail-closed HTTP authority adapter.

    One lazily-created httpx client reuses TCP/TLS connections. Production
    endpoints require HTTPS. Response bytes are consumed through a bounded
    stream before JSON parsing so the declared response limit is a real memory
    boundary rather than a post-buffer size check.
    """

    def __init__(self, base_url: str, token: str = "", timeout_s: float = 2.0,
                 transport: Optional[httpx.BaseTransport] = None, *,
                 allow_loopback_http: bool = False) -> None:
        if not isinstance(token, str):
            raise TypeError("Gatekeeper token must be a string")
        if not _is_number(timeout_s) or not 0 < float(timeout_s) <= 30:
            raise ValueError("Gatekeeper timeout must be in (0, 30] seconds")
        self.base_url = _validate_base_url(base_url, allow_loopback_http=allow_loopback_http)
        self.token = token
        self.timeout_s = float(timeout_s)
        self._transport = transport
        self._client: httpx.Client | None = None
        self._closed = False
        self._client_lock = threading.RLock()

    def _get_client(self) -> httpx.Client:
        with self._client_lock:
            if self._closed:
                raise RuntimeError("Gatekeeper client is closed")
            if self._client is None:
                headers = {"Content-Type": "application/json"}
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"
                self._client = httpx.Client(
                    timeout=self.timeout_s,
                    transport=self._transport,
                    headers=headers,
                    limits=httpx.Limits(max_connections=8, max_keepalive_connections=4,
                                        keepalive_expiry=30.0),
                )
            return self._client

    def close(self) -> None:
        with self._client_lock:
            self._closed = True
            client, self._client = self._client, None
        if client is not None and not client.is_closed:
            client.close()

    def __enter__(self) -> "GatekeeperClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def evaluate(self, evidence: EvidenceFrame, action: ProposedAction) -> AuthorityDecision:
        start = time.perf_counter_ns()
        try:
            body = json.dumps(
                {"evidence": snapshot_fields(evidence), "action": snapshot_fields(action)},
                separators=(",", ":"), allow_nan=False,
            ).encode("utf-8")
            if len(body) > MAX_AUTHORITY_REQUEST_BYTES:
                raise ValueError("authority request exceeds size budget")
        except Exception as exc:
            log.warning("Gatekeeper request for action %s could not be serialized (%s); holding",
                        action.action_id, type(exc).__name__)
            return self._hold(evidence, action, [AUTHORITY_REQUEST_INVALID], start)

        try:
            payload = bytearray()
            with self._get_client().stream("POST", f"{self.base_url}/v1/evaluate", content=body) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    if len(payload) + len(chunk) > MAX_AUTHORITY_RESPONSE_BYTES:
                        raise _AuthorityResponseTooLarge("authority response exceeds size budget")
                    payload.extend(chunk)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            log.warning("Gatekeeper returned HTTP %s for action %s; holding", status, action.action_id)
            return self._hold(evidence, action, [AUTHORITY_UNAVAILABLE, f"HTTP_{status}"], start)
        except _AuthorityResponseTooLarge:
            log.warning("Gatekeeper response exceeded the size budget for action %s; holding", action.action_id)
            return self._hold(evidence, action, [AUTHORITY_RESPONSE_INVALID], start)
        except Exception as exc:
            log.warning("Gatekeeper unreachable or unusable (%s) for action %s; holding",
                        type(exc).__name__, action.action_id)
            return self._hold(evidence, action, [AUTHORITY_UNAVAILABLE], start)

        try:
            parsed = _redact_control_text(_parse_response(json.loads(payload)), self.token)
            return self._decision_from(parsed, evidence, action, start)
        except Exception as exc:
            log.warning("Gatekeeper response malformed (%s) for action %s; holding", type(exc).__name__, action.action_id)
            return self._hold(evidence, action, [AUTHORITY_RESPONSE_INVALID], start)

    def _decision_from(self, parsed: Dict[str, Any], evidence: EvidenceFrame,
                       action: ProposedAction, start: int) -> AuthorityDecision:
        verdict: Verdict = parsed["verdict"]
        reasons: List[str] = parsed["reason_codes"]
        raw_authorized = parsed["authorized_action"]
        authorized: Optional[ProposedAction] = None
        problem: Optional[str] = None

        if verdict == Verdict.ALLOW:
            authorized = action
            if raw_authorized is not None:
                _candidate, problem, changed = _merge_authorized(action, raw_authorized)
                if problem is None and changed:
                    problem = AUTHORIZED_ACTION_CONFLICT
        elif verdict == Verdict.TRANSFORM:
            if raw_authorized is None:
                problem = AUTHORIZED_ACTION_MISSING
            else:
                authorized, problem, changed = _merge_authorized(action, raw_authorized)
                if problem is None and not changed:
                    problem = AUTHORIZED_ACTION_UNCHANGED

        if problem is not None:
            log.warning("Gatekeeper %s for action %s is not executable (%s); holding",
                        verdict.value, action.action_id, problem)
            return self._hold(
                evidence, action, reasons + [problem], start,
                decision_id=parsed["decision_id"], evaluated_at_ms=parsed["evaluated_at_ms"],
                latency=parsed["authority_latency_ms"], policy_version=parsed["policy_version"],
            )
        return AuthorityDecision(
            decision_id=parsed["decision_id"], verdict=verdict, reason_codes=reasons,
            original_action=action,
            authorized_action=authorized if verdict in {Verdict.ALLOW, Verdict.TRANSFORM} else None,
            evidence=evidence, evaluated_at_ms=parsed["evaluated_at_ms"],
            authority_latency_ms=parsed["authority_latency_ms"], policy_version=parsed["policy_version"],
        )

    @staticmethod
    def _hold(evidence: EvidenceFrame, action: ProposedAction, reasons: List[str], start: int,
              *, decision_id: Optional[str] = None, evaluated_at_ms: Optional[int] = None,
              latency: Optional[float] = None,
              policy_version: str = LIVE_UNAVAILABLE_POLICY_VERSION) -> AuthorityDecision:
        elapsed = (time.perf_counter_ns() - start) / 1_000_000.0
        return AuthorityDecision(
            decision_id=decision_id or f"dec-{action.action_id}", verdict=Verdict.HOLD,
            reason_codes=list(reasons), original_action=action, authorized_action=None,
            evidence=evidence,
            evaluated_at_ms=evaluated_at_ms if evaluated_at_ms is not None else int(time.time() * 1000),
            authority_latency_ms=latency if latency is not None else elapsed,
            policy_version=policy_version,
        )


def configured_authority_mode() -> str:
    return os.getenv("AUTHORITY_MODE", "reference").strip().lower()


def describe_authority(authority: AuthorityClient) -> Dict[str, str]:
    if isinstance(authority, GatekeeperClient):
        mode = "live"
    elif isinstance(authority, ReferenceAuthorityEngine):
        mode = "reference"
    else:
        mode = "custom"
    return {"authority_mode": mode, "authority_engine": type(authority).__name__}


def build_authority_client() -> AuthorityClient:
    if configured_authority_mode() == "live":
        return GatekeeperClient(
            os.getenv("GATEKEEPER_URL", ""), os.getenv("GATEKEEPER_TOKEN", ""),
            timeout_s=float(os.getenv("GATEKEEPER_TIMEOUT_S", "0.25")),
        )
    return ReferenceAuthorityEngine(
        evidence_max_age_ms=int(os.getenv("EVIDENCE_MAX_AGE_MS", "500")),
        min_confidence=float(os.getenv("MIN_CONFIDENCE", "0.80")),
        max_speed_mps=float(os.getenv("MAX_SPEED_MPS", "0.35")),
    )
