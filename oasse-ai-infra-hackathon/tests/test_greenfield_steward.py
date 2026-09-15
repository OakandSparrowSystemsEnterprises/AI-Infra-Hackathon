"""Greenfield Steward tests.

These tests prove that agent coordination remains non-authoritative, bounded and
compatible with the existing pre-authority seam.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from oasse_physical_ai.models import EvidenceFrame, ProposedAction, Verdict
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine
from oasse_physical_ai.steward import (
    BindingReviewAgent,
    GreenfieldSteward,
    ProviderStewardAgent,
    StewardError,
    TransitionSummaryAgent,
)


@dataclass
class FakeAgent:
    agent_id: str
    role: str = "test-agent"
    required: bool = False
    fail: bool = False
    assert_authority: bool = False
    mutate: bool = False

    def run(self, evidence, action, artifact):
        if self.mutate:
            action.metadata["tampered"] = True
        if self.fail:
            raise RuntimeError("boom")
        return {
            "authority": True if self.assert_authority else False,
            "artifact_ref": artifact["artifact_ref"],
            "agent": self.agent_id,
        }

    def close(self):
        return None


def fixture():
    evidence = EvidenceFrame.fresh(frame_hash="steward-test")
    action = ProposedAction.pick_place(evidence.evidence_id, speed_mps=0.2)
    return evidence, action


def test_greenfield_steward_is_deterministic_and_non_authoritative():
    evidence, action = fixture()
    steward = GreenfieldSteward([
        TransitionSummaryAgent(), BindingReviewAgent(), FakeAgent("z-review"),
    ])
    first = steward.derive(evidence, action)
    second = steward.derive(evidence, action)
    assert first["authority"] is False
    assert first["plan"]["authority"] is False
    assert first["plan"]["plan_id"] == second["plan"]["plan_id"]
    assert first["state_hash"] == second["state_hash"]
    assert [item["agent_id"] for item in first["agents"]] == sorted(
        item["agent_id"] for item in first["agents"]
    )
    assert first["status"] == "LIVE"


def test_optional_agent_failure_is_isolated_in_observe_mode():
    evidence, action = fixture()
    steward = GreenfieldSteward([
        BindingReviewAgent(), TransitionSummaryAgent(), FakeAgent("optional", fail=True),
    ], required=False)
    record = steward.derive(evidence, action)
    assert record["status"] == "DEGRADED"
    assert record["successful_agents"] == 2
    assert record["failed_agents"] == 1
    assert record["quorum_met"] is True


def test_required_agent_failure_holds_before_gatekeeper_and_actuator():
    calls = {"authority": 0, "actuator": 0}

    class Authority:
        def evaluate(self, evidence, action):
            calls["authority"] += 1
            return ReferenceAuthorityEngine().evaluate(evidence, action)

    class Actuator:
        def execute(self, action):
            calls["actuator"] += 1
            return {"status": "EXECUTED", "action_id": action.action_id}

    steward = GreenfieldSteward([
        BindingReviewAgent(),
        FakeAgent("required-review", required=True, fail=True),
    ], required=True)
    orchestrator = PhysicalAIOrchestrator(
        authority=Authority(), actuator=Actuator(), pre_authority=steward,
    )
    result = orchestrator.run("allow")
    assert result.decision.verdict == Verdict.HOLD
    assert "STEWARD_REQUIRED_AGENT_FAILED" in result.decision.reason_codes
    assert result.dispatch_attempted is False and result.executed is False
    assert calls == {"authority": 0, "actuator": 0}
    assert orchestrator.receipts.verify()
    orchestrator.close()


def test_agent_authority_assertion_is_rejected():
    evidence, action = fixture()
    steward = GreenfieldSteward([
        BindingReviewAgent(), FakeAgent("bad", required=True, assert_authority=True),
    ], required=True)
    with pytest.raises(StewardError) as exc:
        steward.derive(evidence, action)
    assert exc.value.code == "STEWARD_REQUIRED_AGENT_FAILED"


def test_agent_input_mutation_is_isolated_and_rejected():
    evidence, action = fixture()
    steward = GreenfieldSteward([
        BindingReviewAgent(), FakeAgent("mutator", required=True, mutate=True),
    ], required=True)
    with pytest.raises(StewardError) as exc:
        steward.derive(evidence, action)
    assert exc.value.code == "STEWARD_REQUIRED_AGENT_FAILED"
    assert "tampered" not in action.metadata


def test_duplicate_agent_ids_are_rejected_at_configuration_time():
    with pytest.raises(ValueError):
        GreenfieldSteward([FakeAgent("same"), FakeAgent("same")])


def test_steward_integrates_through_existing_orchestrator_without_motion_change():
    steward = GreenfieldSteward([BindingReviewAgent(), TransitionSummaryAgent()])
    orchestrator = PhysicalAIOrchestrator(pre_authority=steward)
    result = orchestrator.run("allow")
    assert result.decision.verdict == Verdict.ALLOW
    assert result.executed is True
    record = result.decision.original_action.metadata["pre_authority_evidence"]["steward"]
    assert record["authority"] is False
    assert record["successful_agents"] == 2
    assert result.decision.original_action.speed_mps == 0.2
    assert [item.receipt_type for item in orchestrator.receipts.all()] == [
        "PRE_AUTHORITY_EVIDENCE", "AUTHORITY_DECISION", "PHYSICAL_OUTCOME"
    ]
    orchestrator.close()
