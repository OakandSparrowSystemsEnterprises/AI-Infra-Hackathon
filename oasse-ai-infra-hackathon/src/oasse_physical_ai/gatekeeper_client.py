from __future__ import annotations

from dataclasses import fields, replace
import json
import logging
import math
import os
import time
from typing import Any, Dict, List, Optional, Protocol, Tuple

import httpx

from .models import PHYSICAL_ACTION_FIELDS, AuthorityDecision, EvidenceFrame, ProposedAction, Verdict, physically_changed
from .policy import ReferenceAuthorityEngine

log = logging.getLogger(__name__)


class AuthorityClient(Protocol):
    def evaluate(self, evidence: EvidenceFrame, action: ProposedAction) -> AuthorityDecision: ...


# Reason codes GatekeeperClient adds itself when it cannot turn the live
# service's answer into an executable decision. Each of them yields a HOLD.
AUTHORITY_REQUEST_INVALID = "AUTHORITY_REQUEST_INVALID"  # the local evidence/action could not be serialized
AUTHORITY_UNAVAILABLE = "AUTHORITY_UNAVAILABLE"  # transport error, timeout, or non-2xx status
AUTHORITY_RESPONSE_INVALID = "AUTHORITY_RESPONSE_INVALID"  # body is not JSON or has missing/invalid fields
AUTHORIZED_ACTION_MISSING = "AUTHORIZED_ACTION_MISSING"  # TRANSFORM without an authorized_action
AUTHORIZED_ACTION_INVALID = "AUTHORIZED_ACTION_INVALID"  # authorized_action is not a usable action
AUTHORIZED_ACTION_UNCHANGED = "AUTHORIZED_ACTION_UNCHANGED"  # TRANSFORM that hands back the proposal
AUTHORIZED_ACTION_BINDING_MISMATCH = "AUTHORIZED_ACTION_BINDING_MISMATCH"  # identity fields differ
AUTHORIZED_ACTION_CONFLICT = "AUTHORIZED_ACTION_CONFLICT"  # ALLOW that carries a different action

LIVE_POLICY_VERSION_DEFAULT = "gatekeeper-live"
LIVE_UNAVAILABLE_POLICY_VERSION = "gatekeeper-live-unavailable"

_BOUND_FIELDS = ("action_id", "actor_id", "evidence_id")
# The only authorized_action fields the adapter applies: the physical fields
# and the identity fields (accepted solely so rebinding can be detected).
# metadata and requested_at_ms are informational, are never taken from the
# service, and keep the proposal's values.
_ACCEPTED_FIELDS = frozenset(PHYSICAL_ACTION_FIELDS) | frozenset(_BOUND_FIELDS)
assert _ACCEPTED_FIELDS <= {f.name for f in fields(ProposedAction)}


def _is_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:  # an int too large for a float
        return False


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _valid_override(name: str, value: Any) -> bool:
    """Type-check one ProposedAction field supplied by the service."""
    if name in ("action_id", "actor_id", "evidence_id", "action_type", "target_bin", "object_id"):
        return _is_text(value)
    if name == "speed_mps":
        return _is_number(value) and value >= 0
    if name == "trajectory":
        return (
            isinstance(value, list)
            and len(value) > 0
            and all(isinstance(point, list) and len(point) > 0 and all(_is_number(c) for c in point) for point in value)
        )
    return False


def _merge_authorized(original: ProposedAction, raw: Any) -> Tuple[Optional[ProposedAction], Optional[str], bool]:
    """Apply the service's authorized_action payload to the proposal.

    `raw` may be a full action object or only the changed fields. Returns
    (candidate, problem, changed). `problem` is a reason code when the payload
    is unusable or rebinds the action to another identity; `changed` says
    whether the candidate differs from the proposal in a physical field.
    """
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
    """Validate the service body. Raises ValueError on any shape or type problem."""
    if not isinstance(data, dict):
        raise ValueError("response body must be a JSON object")
    verdict_raw = data.get("verdict")
    if not isinstance(verdict_raw, str):
        raise ValueError("verdict must be a string")
    verdict = Verdict(verdict_raw)  # ValueError for unknown verdicts
    decision_id = data.get("decision_id")
    if not _is_text(decision_id):
        raise ValueError("decision_id must be a non-empty string")
    # Optional fields: an explicit null is treated like an absent field.
    reasons = data.get("reason_codes")
    if reasons is None:
        reasons = []
    if not isinstance(reasons, list) or not all(isinstance(code, str) for code in reasons):
        raise ValueError("reason_codes must be a list of strings")
    evaluated_at = data.get("evaluated_at_ms")
    if evaluated_at is None:
        evaluated_at = int(time.time() * 1000)
    if not _is_number(evaluated_at) or evaluated_at < 0:
        raise ValueError("evaluated_at_ms must be a non-negative number")
    latency = data.get("authority_latency_ms")
    if latency is None:
        latency = 0.0
    if not _is_number(latency) or latency < 0:
        raise ValueError("authority_latency_ms must be a non-negative number")
    policy_version = data.get("policy_version")
    if policy_version is None:
        policy_version = LIVE_POLICY_VERSION_DEFAULT
    if not _is_text(policy_version):
        raise ValueError("policy_version must be a non-empty string")
    return {
        "verdict": verdict,
        "decision_id": decision_id,
        "reason_codes": list(reasons),
        "evaluated_at_ms": int(evaluated_at),
        "authority_latency_ms": float(latency),
        "policy_version": policy_version,
        "authorized_action": data.get("authorized_action"),
    }


class GatekeeperClient:
    """HTTP adapter for the Gatekeeper authority endpoint.

    This adapter is MIT-licensed repository code. The Gatekeeper production
    service it calls (AUTHORITY_MODE=live with GATEKEEPER_URL) is proprietary
    and is not contained in this repository. See NOTICE.md.

    Expected response from POST {base_url}/v1/evaluate:

        {
          "decision_id": str,                  non-empty
          "verdict": "ALLOW" | "TRANSFORM" | "HOLD" | "DENY",
          "reason_codes": [str, ...],          optional
          "evaluated_at_ms": int,              optional
          "authority_latency_ms": float,       optional, service-reported
          "policy_version": str,               optional
          "authorized_action": {...}           required for TRANSFORM; full
                                               ProposedAction or changed fields
        }

    The adapter fails closed and never raises from evaluate(). Serialization
    problems, transport errors, timeouts, non-2xx statuses, and malformed
    bodies become HOLD decisions carrying a reason code, so the orchestrator
    still seals a decision receipt and the actuator is never reached. A
    TRANSFORM verdict executes only the authorized action returned by the
    service, and only if it differs from the proposal in a physical field;
    it never falls back to the original proposal. An ALLOW that carries a
    different authorized action is a conflict and is held.
    """

    def __init__(
        self,
        base_url: str,
        token: str = "",
        timeout_s: float = 2.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        if not base_url:
            raise ValueError("Gatekeeper base URL is required")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_s = timeout_s
        self._transport = transport

    def evaluate(self, evidence: EvidenceFrame, action: ProposedAction) -> AuthorityDecision:
        start = time.perf_counter_ns()
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Stage 1: serialize the request locally.
        try:
            body = json.dumps({"evidence": evidence.__dict__, "action": action.__dict__}, allow_nan=False).encode("utf-8")
        except Exception as exc:  # noqa: BLE001 - fail closed on anything
            log.warning("Gatekeeper request for action %s could not be serialized (%s); holding", action.action_id, type(exc).__name__)
            return self._hold(evidence, action, [AUTHORITY_REQUEST_INVALID], start)

        # Stage 2: reach the service.
        try:
            with httpx.Client(timeout=self.timeout_s, transport=self._transport) as client:
                response = client.post(f"{self.base_url}/v1/evaluate", content=body, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            log.warning("Gatekeeper returned HTTP %s for action %s; holding", status, action.action_id)
            return self._hold(evidence, action, [AUTHORITY_UNAVAILABLE, f"HTTP_{status}"], start)
        except Exception as exc:  # noqa: BLE001 - transport, TLS, proxy, or client construction failure
            log.warning("Gatekeeper unreachable (%s) for action %s; holding", type(exc).__name__, action.action_id)
            return self._hold(evidence, action, [AUTHORITY_UNAVAILABLE], start)

        # Stage 3: interpret the answer.
        try:
            parsed = _parse_response(response.json())
            return self._decision_from(parsed, evidence, action, start)
        except Exception as exc:  # noqa: BLE001 - not JSON, wrong shape, wrong types, pathological values
            log.warning("Gatekeeper response malformed (%s) for action %s; holding", type(exc).__name__, action.action_id)
            return self._hold(evidence, action, [AUTHORITY_RESPONSE_INVALID], start)

    def _decision_from(self, parsed: Dict[str, Any], evidence: EvidenceFrame, action: ProposedAction, start: int) -> AuthorityDecision:
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
            log.warning("Gatekeeper %s for action %s is not executable (%s); holding", verdict.value, action.action_id, problem)
            return self._hold(
                evidence,
                action,
                reasons + [problem],
                start,
                decision_id=parsed["decision_id"],
                evaluated_at_ms=parsed["evaluated_at_ms"],
                latency=parsed["authority_latency_ms"],
                policy_version=parsed["policy_version"],
            )
        return AuthorityDecision(
            decision_id=parsed["decision_id"],
            verdict=verdict,
            reason_codes=reasons,
            original_action=action,
            authorized_action=authorized if verdict in {Verdict.ALLOW, Verdict.TRANSFORM} else None,
            evidence=evidence,
            evaluated_at_ms=parsed["evaluated_at_ms"],
            authority_latency_ms=parsed["authority_latency_ms"],
            policy_version=parsed["policy_version"],
        )

    @staticmethod
    def _hold(
        evidence: EvidenceFrame,
        action: ProposedAction,
        reasons: List[str],
        start: int,
        *,
        decision_id: Optional[str] = None,
        evaluated_at_ms: Optional[int] = None,
        latency: Optional[float] = None,
        policy_version: str = LIVE_UNAVAILABLE_POLICY_VERSION,
    ) -> AuthorityDecision:
        """Fail-closed decision: nothing is authorized, and the receipt records why.

        When no service-reported latency exists, the local time elapsed until
        the failure is recorded instead.
        """
        elapsed = (time.perf_counter_ns() - start) / 1_000_000.0
        return AuthorityDecision(
            decision_id=decision_id or f"dec-{action.action_id}",
            verdict=Verdict.HOLD,
            reason_codes=list(reasons),
            original_action=action,
            authorized_action=None,
            evidence=evidence,
            evaluated_at_ms=evaluated_at_ms if evaluated_at_ms is not None else int(time.time() * 1000),
            authority_latency_ms=latency if latency is not None else elapsed,
            policy_version=policy_version,
        )


def configured_authority_mode() -> str:
    """The AUTHORITY_MODE setting as the code interprets it (trimmed, lowercased)."""
    return os.getenv("AUTHORITY_MODE", "reference").strip().lower()


def describe_authority(authority: AuthorityClient) -> Dict[str, str]:
    """Report which authority engine is actually wired in, for /health and judges."""
    if isinstance(authority, GatekeeperClient):
        mode = "live"
    elif isinstance(authority, ReferenceAuthorityEngine):
        mode = "reference"
    else:
        mode = "custom"
    return {"authority_mode": mode, "authority_engine": type(authority).__name__}


def build_authority_client() -> AuthorityClient:
    if configured_authority_mode() == "live":
        return GatekeeperClient(os.getenv("GATEKEEPER_URL", ""), os.getenv("GATEKEEPER_TOKEN", ""))
    return ReferenceAuthorityEngine(
        evidence_max_age_ms=int(os.getenv("EVIDENCE_MAX_AGE_MS", "500")),
        min_confidence=float(os.getenv("MIN_CONFIDENCE", "0.80")),
        max_speed_mps=float(os.getenv("MAX_SPEED_MPS", "0.35")),
    )
