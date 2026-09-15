"""Greenfield, non-authoritative agent steward for pre-authority evidence.

This module is independently authored for the AI Infra project. It coordinates
bounded evidence/review agents after a planner proposes an action and before
Gatekeeper evaluates that action. The steward can never authorize execution and
cannot modify executable action fields.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib
import json
import math
import os
import time
from typing import Any, Protocol

from .dispatch import copy_action, copy_evidence
from .models import EvidenceFrame, ProposedAction
from .normalization import plain
from .tenki import (
    PreAuthorityEvidenceProvider,
    TenkiEvidenceError,
    build_artifact,
    build_tenki_provider,
    requested_effect,
)

STEWARD_SCHEMA = "oasse.greenfield-steward.v1"
STEWARD_PLAN_SCHEMA = "oasse.greenfield-steward-plan.v1"
MAX_STEWARD_AGENTS = 16
MAX_AGENT_RESULT_BYTES = 64 * 1024
MAX_STEWARD_RECORD_BYTES = 256 * 1024

_FORBIDDEN_AUTHORITY_FIELDS = {
    "authority",
    "permit",
    "capability",
    "token",
    "gatekeeper_verdict",
    "authorized_action",
    "verdict",
}


class StewardError(TenkiEvidenceError):
    """Compatibility error carrying a bounded pre-authority failure code."""


class StewardAgent(Protocol):
    agent_id: str
    role: str
    required: bool

    def run(
        self,
        evidence: EvidenceFrame,
        action: ProposedAction,
        artifact: dict[str, Any],
    ) -> dict[str, Any]: ...

    def close(self) -> None: ...


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise StewardError(f"STEWARD_{name.upper()}_INVALID")
    return value


def _assert_non_authoritative(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _FORBIDDEN_AUTHORITY_FIELDS:
                if key == "authority":
                    if child is not False:
                        raise StewardError("STEWARD_AGENT_AUTHORITY_ASSERTION")
                elif child not in (None, False):
                    raise StewardError("STEWARD_AGENT_AUTHORITY_ASSERTION")
            _assert_non_authoritative(child)
    elif isinstance(value, list):
        for child in value:
            _assert_non_authoritative(child)


def _validate_agent_result(
    result: Any,
    *,
    artifact: dict[str, Any],
    effect: str,
    principal: str,
) -> dict[str, Any]:
    try:
        normalized = plain(result, max_depth=16, max_nodes=4096)
        encoded = _canonical(normalized)
    except Exception as exc:
        raise StewardError("STEWARD_AGENT_RESULT_INVALID") from exc
    if not isinstance(normalized, dict):
        raise StewardError("STEWARD_AGENT_RESULT_INVALID")
    if len(encoded) > MAX_AGENT_RESULT_BYTES:
        raise StewardError("STEWARD_AGENT_RESULT_TOO_LARGE")
    _assert_non_authoritative(normalized)
    if normalized.get("authority") is not False:
        raise StewardError("STEWARD_AGENT_AUTHORITY_ASSERTION")

    bindings = {
        "artifact_ref": artifact["artifact_ref"],
        "artifact_sha256": artifact["artifact_sha256"],
        "requested_effect": effect,
        "principal": principal,
    }
    for key, expected in bindings.items():
        if key in normalized and normalized[key] != expected:
            raise StewardError("STEWARD_AGENT_BINDING_MISMATCH")
    return normalized


@dataclass
class ProviderStewardAgent:
    """Wrap an existing pre-authority provider as a Steward-managed agent."""

    agent_id: str
    role: str
    provider: PreAuthorityEvidenceProvider
    required: bool = False

    def __post_init__(self) -> None:
        _text(self.agent_id, "agent_id")
        _text(self.role, "role")
        if not hasattr(self.provider, "derive"):
            raise TypeError("provider must implement derive")

    def run(self, evidence: EvidenceFrame, action: ProposedAction,
            artifact: dict[str, Any]) -> dict[str, Any]:
        return self.provider.derive(evidence, action)

    def close(self) -> None:
        close = getattr(self.provider, "close", None)
        if callable(close):
            close()


@dataclass
class BindingReviewAgent:
    """Deterministic identity/binding review; evidence only, never permission."""

    agent_id: str = "binding-review"
    role: str = "evidence-action-binding-review"
    required: bool = True

    def run(self, evidence: EvidenceFrame, action: ProposedAction,
            artifact: dict[str, Any]) -> dict[str, Any]:
        if action.evidence_id != evidence.evidence_id:
            raise StewardError("STEWARD_EVIDENCE_BINDING_MISMATCH")
        return {
            "authority": False,
            "review": "binding",
            "evidence_id": evidence.evidence_id,
            "action_id": action.action_id,
            "actor_id": action.actor_id,
            "artifact_ref": artifact["artifact_ref"],
            "artifact_sha256": artifact["artifact_sha256"],
            "evidence_sha256": artifact["evidence_sha256"],
            "action_sha256": artifact["action_sha256"],
            "binding_match": True,
        }

    def close(self) -> None:
        return None


@dataclass
class TransitionSummaryAgent:
    """Deterministically summarizes the proposed physical transition."""

    agent_id: str = "transition-summary"
    role: str = "physical-transition-summary"
    required: bool = True

    def run(self, evidence: EvidenceFrame, action: ProposedAction,
            artifact: dict[str, Any]) -> dict[str, Any]:
        path_length = 0.0
        max_segment = 0.0
        points = action.trajectory
        for left, right in zip(points, points[1:]):
            segment = math.sqrt(sum((float(b) - float(a)) ** 2 for a, b in zip(left, right)))
            path_length += segment
            max_segment = max(max_segment, segment)
        return {
            "authority": False,
            "review": "transition-summary",
            "artifact_ref": artifact["artifact_ref"],
            "action_id": action.action_id,
            "action_type": action.action_type,
            "object_id": action.object_id,
            "target_bin": action.target_bin,
            "speed_mps": action.speed_mps,
            "trajectory_points": len(points),
            "path_length_m": path_length,
            "max_segment_m": max_segment,
            "workspace_clear_observed": evidence.workspace_clear,
            "confidence_observed": evidence.confidence,
            "anomaly_score_observed": evidence.anomaly_score,
        }

    def close(self) -> None:
        return None


class GreenfieldSteward:
    """Parallel, deterministic coordinator for non-authoritative review agents."""

    name = "steward"

    def __init__(self, agents: list[StewardAgent], *, required: bool = False,
                 min_successes: int | None = None) -> None:
        if not isinstance(agents, list) or not 1 <= len(agents) <= MAX_STEWARD_AGENTS:
            raise ValueError(f"steward requires 1 to {MAX_STEWARD_AGENTS} agents")
        ids: set[str] = set()
        for agent in agents:
            agent_id = _text(getattr(agent, "agent_id", None), "agent_id")
            _text(getattr(agent, "role", None), "role")
            if agent_id in ids:
                raise ValueError("steward agent IDs must be unique")
            ids.add(agent_id)
        self.agents = list(agents)
        self.required = bool(required)
        default_min = sum(1 for agent in agents if bool(getattr(agent, "required", False)))
        default_min = max(1, default_min)
        selected = default_min if min_successes is None else min_successes
        if type(selected) is not int or not 1 <= selected <= len(agents):
            raise ValueError("min_successes must be within the configured agent count")
        self.min_successes = selected

    def close(self) -> None:
        for agent in self.agents:
            try:
                agent.close()
            except Exception:
                pass

    def _plan(self, artifact: dict[str, Any], effect: str, principal: str) -> dict[str, Any]:
        roster = [
            {
                "agent_id": agent.agent_id,
                "role": agent.role,
                "required": bool(agent.required),
                "authority": False,
            }
            for agent in sorted(self.agents, key=lambda item: item.agent_id)
        ]
        seed = {
            "schema": STEWARD_PLAN_SCHEMA,
            "artifact_ref": artifact["artifact_ref"],
            "requested_effect": effect,
            "principal": principal,
            "agents": roster,
            "authority": False,
        }
        return {**seed, "plan_id": _digest(seed)}

    def _run_agent(self, agent: StewardAgent, evidence: EvidenceFrame,
                   action: ProposedAction, artifact: dict[str, Any], effect: str,
                   principal: str) -> dict[str, Any]:
        started = time.perf_counter_ns()
        safe_evidence = copy_evidence(evidence)
        safe_action = copy_action(action)
        agent_evidence = copy_evidence(safe_evidence)
        agent_action = copy_action(safe_action)
        try:
            raw = agent.run(agent_evidence, agent_action, dict(artifact))
            if agent_evidence != safe_evidence or agent_action != safe_action:
                raise StewardError("STEWARD_AGENT_INPUT_MUTATED")
            result = _validate_agent_result(
                raw, artifact=artifact, effect=effect, principal=principal,
            )
            semantic = {
                "agent_id": agent.agent_id,
                "role": agent.role,
                "required": bool(agent.required),
                "status": "COMPLETED",
                "authority": False,
                "artifact_ref": artifact["artifact_ref"],
                "result": result,
            }
            return {
                **semantic,
                "result_hash": _digest(semantic),
                "elapsed_ms": (time.perf_counter_ns() - started) / 1e6,
            }
        except Exception as exc:
            code = getattr(exc, "code", None)
            if not isinstance(code, str) or not code:
                code = "STEWARD_AGENT_FAILED"
            semantic = {
                "agent_id": agent.agent_id,
                "role": agent.role,
                "required": bool(agent.required),
                "status": "FAILED",
                "authority": False,
                "artifact_ref": artifact["artifact_ref"],
                "error_code": code,
            }
            return {
                **semantic,
                "result_hash": _digest(semantic),
                "elapsed_ms": (time.perf_counter_ns() - started) / 1e6,
            }

    def derive(self, evidence: EvidenceFrame, action: ProposedAction) -> dict[str, Any]:
        started = time.perf_counter_ns()
        artifact = build_artifact(evidence, action)
        effect = requested_effect(action)
        principal = _text(action.actor_id, "principal")
        plan = self._plan(artifact, effect, principal)

        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=len(self.agents), thread_name_prefix="oasse-steward") as pool:
            futures = {
                pool.submit(
                    self._run_agent, agent, evidence, action, artifact, effect, principal
                ): agent.agent_id
                for agent in self.agents
            }
            for future in as_completed(futures):
                results.append(future.result())
        results.sort(key=lambda item: item["agent_id"])

        successes = [item for item in results if item["status"] == "COMPLETED"]
        failures = [item for item in results if item["status"] == "FAILED"]
        required_failures = [item for item in failures if item["required"]]
        quorum_met = len(successes) >= self.min_successes

        aggregate = {
            "schema": STEWARD_SCHEMA,
            "plan_id": plan["plan_id"],
            "artifact_ref": artifact["artifact_ref"],
            "requested_effect": effect,
            "principal": principal,
            "authority": False,
            "agent_result_hashes": [item["result_hash"] for item in results],
            "successful_agents": len(successes),
            "failed_agents": len(failures),
            "required_failures": len(required_failures),
            "quorum_met": quorum_met,
        }
        state_hash = _digest(aggregate)

        if self.required and required_failures:
            raise StewardError("STEWARD_REQUIRED_AGENT_FAILED")
        if self.required and not quorum_met:
            raise StewardError("STEWARD_QUORUM_UNMET")

        record = {
            "schema": STEWARD_SCHEMA,
            "provider": "steward",
            "status": "LIVE" if not failures and quorum_met else "DEGRADED",
            "authority": False,
            "required": self.required,
            **artifact,
            "requested_effect": effect,
            "principal": principal,
            "plan": plan,
            "agents": results,
            "agent_count": len(results),
            "successful_agents": len(successes),
            "failed_agents": len(failures),
            "quorum_met": quorum_met,
            "state_hash": state_hash,
            "elapsed_ms": (time.perf_counter_ns() - started) / 1e6,
        }
        try:
            normalized = plain(record, max_depth=20, max_nodes=10000)
            if len(_canonical(normalized)) > MAX_STEWARD_RECORD_BYTES:
                raise StewardError("STEWARD_RECORD_TOO_LARGE")
        except StewardError:
            raise
        except Exception as exc:
            raise StewardError("STEWARD_RECORD_INVALID") from exc
        return normalized


def configured_steward_mode() -> str:
    mode = os.getenv("STEWARD_MODE", "off").strip().lower()
    if mode not in {"off", "observe", "required"}:
        raise ValueError("STEWARD_MODE must be off, observe, or required")
    return mode


def build_greenfield_steward_from_env() -> GreenfieldSteward:
    """Create the independently authored Steward without changing default runtime behavior."""
    mode = configured_steward_mode()
    if mode == "off":
        raise ValueError("STEWARD_MODE is off")

    agents: list[StewardAgent] = [BindingReviewAgent(), TransitionSummaryAgent()]
    tenki = build_tenki_provider()
    if tenki is not None:
        agents.append(ProviderStewardAgent(
            agent_id="tenki-derive",
            role="isolated-derived-evidence",
            provider=tenki,
            required=bool(getattr(tenki, "required", False)),
        ))

    raw_min = os.getenv("STEWARD_MIN_SUCCESSES", "").strip()
    min_successes = None if not raw_min else int(raw_min)
    return GreenfieldSteward(
        agents,
        required=mode == "required",
        min_successes=min_successes,
    )
