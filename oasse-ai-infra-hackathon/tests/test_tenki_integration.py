"""Tenki pre-authority integration tests.

The tests prove that Tenki can add bounded, non-authoritative derived evidence
without changing the existing physical action semantics or becoming authority.
"""
from __future__ import annotations

import hashlib
import json

import httpx

from oasse_physical_ai.models import EvidenceFrame, ProposedAction, Verdict
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine
from oasse_physical_ai.tenki import (
    MAX_TENKI_RESPONSE_BYTES,
    TenkiDerivedEvidenceClient,
    build_artifact,
    requested_effect,
)


def _valid_handler(captured: list[dict] | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if captured is not None:
            captured.append(body)
        semantic = {
            "artifact_ref": body["artifact_ref"],
            "artifact_sha256": body["artifact_sha256"],
            "requested_effect": body["requested_effect"],
            "principal": body["principal"],
            "authority": False,
            "compute_plane": "tenki",
            "role": "derived_claim_only",
            "kind": "physical_action_artifact_derivation",
        }
        claim_hash = hashlib.sha256(
            json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return httpx.Response(200, json={"ok": True, "claim": {**semantic, "claim_hash": claim_hash}})
    return handler


def _client(*, required: bool = False, handler=None) -> TenkiDerivedEvidenceClient:
    return TenkiDerivedEvidenceClient(
        "https://tenki.test/derive",
        required=required,
        transport=httpx.MockTransport(handler or _valid_handler()),
    )


def test_tenki_artifact_binds_exact_evidence_and_proposal_without_preauthority_recursion():
    evidence = EvidenceFrame.fresh(frame_hash="tenki-frame", scene_hash="scene-1")
    action = ProposedAction.pick_place(evidence.evidence_id, speed_mps=0.2,
        metadata={"planner": "test"})
    first = build_artifact(evidence, action)
    enriched = ProposedAction(**{
        **action.__dict__,
        "metadata": {**action.metadata, "pre_authority_evidence": {"tenki": {"claim_hash": "a" * 64}}},
    })
    second = build_artifact(evidence, enriched)
    assert first == second
    assert first["artifact_ref"] == "sha256:" + first["artifact_sha256"]
    assert requested_effect(action).startswith("physical-ai.execute:pick_place")


def test_valid_tenki_claim_is_bound_into_action_before_authority_without_changing_motion():
    captured: list[dict] = []
    client = _client(handler=_valid_handler(captured))
    orchestrator = PhysicalAIOrchestrator(pre_authority=client)
    result = orchestrator.run("allow")
    assert result.decision.verdict == Verdict.ALLOW
    assert result.executed is True
    original = result.decision.original_action
    claim = original.metadata["pre_authority_evidence"]["tenki"]
    assert claim["authority"] is False
    assert claim["compute_plane"] == "tenki"
    assert claim["role"] == "derived_claim_only"
    assert claim["artifact_ref"] == captured[0]["artifact_ref"]
    assert original.speed_mps == 0.2
    assert result.decision.authorized_action == original
    assert [receipt.receipt_type for receipt in orchestrator.receipts.all()] == [
        "PRE_AUTHORITY_EVIDENCE", "AUTHORITY_DECISION", "PHYSICAL_OUTCOME"
    ]
    assert orchestrator.receipts.verify()
    orchestrator.close()


def test_transform_remains_gatekeeper_owned_after_tenki_derivation():
    orchestrator = PhysicalAIOrchestrator(pre_authority=_client())
    result = orchestrator.run("overspeed")
    assert result.decision.verdict == Verdict.TRANSFORM
    assert result.executed is True
    assert result.decision.original_action.speed_mps == 0.8
    assert result.decision.authorized_action.speed_mps == 0.35
    assert result.decision.original_action.metadata["pre_authority_evidence"]["tenki"]["authority"] is False
    orchestrator.close()


def test_required_tenki_rejects_authority_assertion_and_never_dispatches():
    calls = {"authority": 0, "actuator": 0}

    class Authority:
        def evaluate(self, evidence, action):
            calls["authority"] += 1
            return ReferenceAuthorityEngine().evaluate(evidence, action)

    class Actuator:
        def execute(self, action):
            calls["actuator"] += 1
            return {"status": "EXECUTED", "action_id": action.action_id}

    def bad_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        return httpx.Response(200, json={"ok": True, "claim": {
            "artifact_ref": body["artifact_ref"],
            "artifact_sha256": body["artifact_sha256"],
            "requested_effect": body["requested_effect"],
            "principal": body["principal"],
            "authority": True,
            "compute_plane": "tenki",
            "role": "derived_claim_only",
            "claim_hash": "a" * 64,
        }})

    orchestrator = PhysicalAIOrchestrator(
        authority=Authority(), actuator=Actuator(),
        pre_authority=_client(required=True, handler=bad_handler),
    )
    result = orchestrator.run()
    assert result.decision.verdict == Verdict.HOLD
    assert "TENKI_AUTHORITY_ASSERTION" in result.decision.reason_codes
    assert result.dispatch_attempted is False and result.executed is False
    assert calls == {"authority": 0, "actuator": 0}
    assert orchestrator.receipts.verify()
    orchestrator.close()


def test_observe_mode_tenki_outage_does_not_break_existing_authority_path():
    def unavailable(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    orchestrator = PhysicalAIOrchestrator(pre_authority=_client(handler=unavailable))
    result = orchestrator.run("allow")
    assert result.decision.verdict == Verdict.ALLOW
    assert result.executed is True
    assert "pre_authority_evidence" not in result.decision.original_action.metadata
    pre = orchestrator.receipts.all()[0]
    assert pre.receipt_type == "PRE_AUTHORITY_EVIDENCE"
    assert pre.payload["authority"] is False
    assert pre.payload["status"] == "UNAVAILABLE"
    orchestrator.close()


def test_planner_cannot_spoof_reserved_preauthority_metadata():
    class SpoofingPlanner:
        def propose(self, evidence, scenario="live"):
            return ProposedAction.pick_place(evidence.evidence_id,
                metadata={"pre_authority_evidence": {"tenki": {"authority": False, "status": "LIVE"}}})

    orchestrator = PhysicalAIOrchestrator(vla=SpoofingPlanner(), pre_authority=_client())
    result = orchestrator.run()
    assert result.decision.verdict == Verdict.HOLD
    assert result.decision.reason_codes == ["PRE_AUTHORITY_METADATA_RESERVED"]
    assert result.dispatch_attempted is False
    orchestrator.close()


def test_tenki_response_is_bounded_before_json_parse():
    def oversized(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b'{"padding":"' + b'x' * MAX_TENKI_RESPONSE_BYTES + b'"}')

    client = _client(required=True, handler=oversized)
    orchestrator = PhysicalAIOrchestrator(pre_authority=client)
    result = orchestrator.run()
    assert result.decision.verdict == Verdict.HOLD
    assert "TENKI_RESPONSE_TOO_LARGE" in result.decision.reason_codes
    assert not result.dispatch_attempted
    orchestrator.close()
