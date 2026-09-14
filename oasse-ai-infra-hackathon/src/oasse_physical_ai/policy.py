"""MIT-licensed reference policy. Not the proprietary Gatekeeper engine."""
from __future__ import annotations

from dataclasses import replace
import time
from typing import Set

from .models import AuthorityDecision, EvidenceFrame, ProposedAction, Verdict


class ReferenceAuthorityEngine:
    """Small declared demo policy; production authority remains behind the API."""

    def __init__(self, evidence_max_age_ms: int = 500, min_confidence: float = 0.80,
                 max_speed_mps: float = 0.35, allowed_actors: Set[str] | None = None) -> None:
        from .normalization import integer, number, text
        self.evidence_max_age_ms = integer(evidence_max_age_ms, "evidence_max_age_ms")
        self.min_confidence = number(min_confidence, "min_confidence", minimum=0, maximum=1)
        self.max_speed_mps = number(max_speed_mps, "max_speed_mps", minimum=0)
        self.allowed_actors = {"vla-planner-1", "operator-approved-vla"} if allowed_actors is None else set(allowed_actors)
        for actor in self.allowed_actors:
            text(actor, "allowed_actor")

    def evaluate(self, evidence: EvidenceFrame, action: ProposedAction, now_ms: int | None = None) -> AuthorityDecision:
        start = time.perf_counter_ns()
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        reasons: list[str] = []
        verdict = Verdict.ALLOW
        authorized = action
        if action.actor_id not in self.allowed_actors:
            verdict = Verdict.DENY
            reasons.append("ACTOR_NOT_AUTHORIZED")
        if action.evidence_id != evidence.evidence_id:
            verdict = Verdict.DENY
            reasons.append("EVIDENCE_BINDING_MISMATCH")
        age = now_ms - evidence.captured_at_ms
        if verdict != Verdict.DENY and age < 0:
            verdict = Verdict.HOLD
            reasons.append("EVIDENCE_IN_FUTURE")
        if verdict != Verdict.DENY and age > self.evidence_max_age_ms:
            verdict = Verdict.HOLD
            reasons.append("EVIDENCE_STALE")
        if verdict != Verdict.DENY and not evidence.workspace_clear:
            verdict = Verdict.DENY
            reasons.append("WORKSPACE_OCCUPIED")
        if verdict == Verdict.ALLOW and evidence.confidence < self.min_confidence:
            verdict = Verdict.HOLD
            reasons.append("EVIDENCE_CONFIDENCE_LOW")
        if verdict == Verdict.ALLOW and action.action_type != "pick_place":
            verdict = Verdict.HOLD
            reasons.append("ACTION_NOT_IN_POLICY")
        if verdict == Verdict.ALLOW and action.target_bin not in {"accept", "reject"}:
            verdict = Verdict.DENY
            reasons.append("TARGET_OUTSIDE_AUTHORIZED_BINS")
        if verdict == Verdict.ALLOW and action.speed_mps > self.max_speed_mps:
            verdict = Verdict.TRANSFORM
            reasons.append("SPEED_CLAMPED")
            authorized = replace(action, speed_mps=self.max_speed_mps)
        if verdict in {Verdict.HOLD, Verdict.DENY}:
            authorized = None
        if not reasons:
            reasons.append("POLICY_SATISFIED")
        return AuthorityDecision(
            decision_id=f"dec-{action.action_id}", verdict=verdict, reason_codes=reasons,
            original_action=action, authorized_action=authorized, evidence=evidence,
            evaluated_at_ms=now_ms, authority_latency_ms=(time.perf_counter_ns() - start) / 1e6)
