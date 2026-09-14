"""Non-actuating contract checks against an explicitly configured authority endpoint."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import time
from urllib.parse import urlsplit

import httpx

from .dispatch import copy_action
from .gatekeeper_client import GatekeeperClient
from .models import EvidenceFrame, ProposedAction, Verdict
from .normalization import number, text
from .orchestrator import PhysicalAIOrchestrator


def endpoint_url(value: str, *, allow_loopback_http: bool = False) -> str:
    text(value, "GATEKEEPER_URL")
    url = urlsplit(value)
    if value != value.strip() or any(ord(char) < 33 for char in value):
        raise ValueError("endpoint contains whitespace or control characters")
    if url.username or url.password or url.query or url.fragment or not url.hostname:
        raise ValueError("endpoint must not contain credentials, a query, or a fragment")
    allowed_http = allow_loopback_http and url.hostname in {"127.0.0.1", "localhost", "::1"}
    if url.scheme != "https" and not (url.scheme == "http" and allowed_http):
        raise ValueError("HTTPS is required except explicitly enabled loopback HTTP")
    if url.path.rstrip("/").endswith("/v1/evaluate"):
        raise ValueError("GATEKEEPER_URL must be the base URL, not /v1/evaluate")
    _ = url.port
    return value.rstrip("/")


def probe_gatekeeper(url: str, *, expected_policy_version: str, token: str = "",
                     timeout_s: float = 2., max_speed_mps: float = .35,
                     allow_loopback_http: bool = False,
                     transport: httpx.BaseTransport | None = None) -> dict:
    base = endpoint_url(url, allow_loopback_http=allow_loopback_http)
    text(expected_policy_version, "expected_policy_version")
    number(timeout_s, "timeout_s", minimum=.01, maximum=10)
    ceiling = number(max_speed_mps, "max_speed_mps", minimum=.001, maximum=1.)
    client = GatekeeperClient(base, token, timeout_s, transport)
    orchestrator = PhysicalAIOrchestrator(authority=client)
    try:
        fixtures = (("allow", "ALLOW"), ("overspeed", "TRANSFORM"), ("stale", "HOLD"),
                    ("occupied", "DENY"), ("low_confidence", "HOLD"), ("binding_mismatch", "DENY"))
        checks = []
        for name, expected_verdict in fixtures:
            evidence = EvidenceFrame.fresh(confidence=.99, workspace_clear=True, anomaly_score=0.,
                frame_hash=hashlib.sha256(b"oasse-non-actuating-contract-fixture").hexdigest(),
                metadata={"source": "synthetic-contract-fixture", "actuation_permitted_by_probe": False})
            action = ProposedAction.pick_place(evidence.evidence_id, speed_mps=min(.2, ceiling),
                                               trajectory=[[0., 0., .1], [.02, 0., .1]])
            if name == "overspeed": action = replace(action, speed_mps=ceiling*2)
            if name == "stale": evidence = replace(evidence, captured_at_ms=evidence.captured_at_ms-60000)
            if name == "occupied": evidence = replace(evidence, workspace_clear=False)
            if name == "low_confidence": evidence = replace(evidence, confidence=0.)
            if name == "binding_mismatch": action = replace(action, evidence_id="mismatched-evidence")
            started = time.perf_counter_ns()
            decision = orchestrator.evaluate_only(evidence, action)
            round_trip = (time.perf_counter_ns()-started)/1e6
            compatible = (decision.verdict.value == expected_verdict
                          and decision.policy_version == expected_policy_version)
            if expected_verdict == "ALLOW":
                compatible &= decision.authorized_action == action
            elif expected_verdict == "TRANSFORM":
                authorized = decision.authorized_action
                compatible &= authorized is not None
                if authorized is not None:
                    compatible &= 0 <= authorized.speed_mps <= ceiling and authorized.speed_mps < action.speed_mps
                    compatible &= copy_action(authorized) == replace(action, speed_mps=authorized.speed_mps)
            else:
                compatible &= decision.authorized_action is None
            unavailable = any(code.startswith(("AUTHORITY_", "AUTHORIZED_ACTION_"))
                              for code in decision.reason_codes)
            compatible &= not unavailable
            checks.append({"scenario": name, "passed": bool(compatible), "expected_verdict": expected_verdict,
                           "verdict": decision.verdict.value, "reason_codes": decision.reason_codes,
                           "policy_version": decision.policy_version,
                           "service_authority_latency_ms": decision.authority_latency_ms,
                           "client_evaluate_elapsed_ms": round_trip})
        report = {"schema": "oasse.gatekeeper-probe.v1", "passed": all(c["passed"] for c in checks),
                  "checked_at_ms": int(time.time()*1000), "endpoint": base,
                  "endpoint_scope": "loopback-fixture" if urlsplit(base).hostname in {"127.0.0.1", "localhost", "::1"} else "configured-service",
                  "connection_mode": "injected-test-transport" if transport is not None else "http-network",
                  "expected_policy_version": expected_policy_version, "checks": checks,
                  "actuator_calls": 0, "physical_execution_tested": False,
                  "service_identity_attested": False,
                  "receipt_chain_valid": orchestrator.receipts.verify()}
    finally:
        orchestrator.close()

    def redacted(value):
        if isinstance(value, str):
            return value.replace(token, "[REDACTED]") if token else value
        if isinstance(value, list):
            return [redacted(item) for item in value]
        if isinstance(value, dict):
            return {key: redacted(item) for key, item in value.items()}
        return value
    return redacted(report)
