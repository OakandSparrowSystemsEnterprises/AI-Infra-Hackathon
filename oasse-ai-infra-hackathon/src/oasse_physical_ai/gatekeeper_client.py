from __future__ import annotations

import os
from typing import Protocol
import httpx

from .models import AuthorityDecision, EvidenceFrame, ProposedAction, Verdict
from .policy import ReferenceAuthorityEngine


class AuthorityClient(Protocol):
    def evaluate(self, evidence: EvidenceFrame, action: ProposedAction) -> AuthorityDecision: ...


class GatekeeperClient:
    """HTTP adapter for the proprietary Gatekeeper authority endpoint."""

    def __init__(self, base_url: str, token: str = "", timeout_s: float = 2.0) -> None:
        if not base_url:
            raise ValueError("Gatekeeper base URL is required")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_s = timeout_s

    def evaluate(self, evidence: EvidenceFrame, action: ProposedAction) -> AuthorityDecision:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        payload = {"evidence": evidence.__dict__, "action": action.__dict__}
        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.post(f"{self.base_url}/v1/evaluate", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return AuthorityDecision(
            decision_id=data["decision_id"],
            verdict=Verdict(data["verdict"]),
            reason_codes=data.get("reason_codes", []),
            original_action=action,
            authorized_action=action if data["verdict"] in {"ALLOW", "TRANSFORM"} else None,
            evidence=evidence,
            evaluated_at_ms=data.get("evaluated_at_ms", 0),
            authority_latency_ms=float(data.get("authority_latency_ms", 0.0)),
            policy_version=data.get("policy_version", "gatekeeper-live"),
        )


def build_authority_client() -> AuthorityClient:
    mode = os.getenv("AUTHORITY_MODE", "reference").strip().lower()
    if mode == "live":
        return GatekeeperClient(os.getenv("GATEKEEPER_URL", ""), os.getenv("GATEKEEPER_TOKEN", ""))
    return ReferenceAuthorityEngine(
        evidence_max_age_ms=int(os.getenv("EVIDENCE_MAX_AGE_MS", "500")),
        min_confidence=float(os.getenv("MIN_CONFIDENCE", "0.80")),
        max_speed_mps=float(os.getenv("MAX_SPEED_MPS", "0.35")),
    )
