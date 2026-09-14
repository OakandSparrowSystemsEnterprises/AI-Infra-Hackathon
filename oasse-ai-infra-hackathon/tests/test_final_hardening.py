"""Final adversarial checks for hot-path isolation, pooling and strict contracts."""
from __future__ import annotations

import json
from unittest import mock

import httpx
import pytest

from oasse_physical_ai.dispatch import DispatchGuard
from oasse_physical_ai.gatekeeper_client import GatekeeperClient, AUTHORITY_RESPONSE_INVALID, AUTHORIZED_ACTION_INVALID
from oasse_physical_ai.models import EvidenceFrame, ProposedAction, Verdict
from oasse_physical_ai.policy import ReferenceAuthorityEngine


def fixture():
    evidence = EvidenceFrame.fresh(frame_hash="final-hardening")
    action = ProposedAction.pick_place(evidence.evidence_id)
    return evidence, action


def response(request, **overrides):
    body = json.loads(request.content)
    decision = ReferenceAuthorityEngine().evaluate(EvidenceFrame(**body["evidence"]), ProposedAction(**body["action"]))
    data = decision.to_dict(); data.update(overrides)
    return httpx.Response(200, json=data)


def test_gatekeeper_constructs_one_http_client_and_reuses_it():
    real_client = httpx.Client; constructions = 0; calls = 0
    def transport_handler(request):
        nonlocal calls; calls += 1; return response(request)
    def client_factory(*args, **kwargs):
        nonlocal constructions; constructions += 1; return real_client(*args, **kwargs)
    with mock.patch("oasse_physical_ai.gatekeeper_client.httpx.Client", side_effect=client_factory):
        client = GatekeeperClient("https://gatekeeper.test", transport=httpx.MockTransport(transport_handler))
        evidence, action = fixture()
        assert client.evaluate(evidence, action).verdict == Verdict.ALLOW
        assert client.evaluate(evidence, action).verdict == Verdict.ALLOW
        assert constructions == 1 and calls == 2
        client.close(); client.close()


def test_plain_http_authority_endpoint_is_rejected_before_token_can_be_sent():
    with pytest.raises(ValueError):
        GatekeeperClient("http://example.com", token="secret")


def test_live_response_timestamp_must_be_exact_integer():
    evidence, action = fixture()
    client = GatekeeperClient("https://gatekeeper.test", transport=httpx.MockTransport(
        lambda request: response(request, evaluated_at_ms=1700000000000.5)))
    decision = client.evaluate(evidence, action)
    assert decision.verdict == Verdict.HOLD
    assert decision.reason_codes == [AUTHORITY_RESPONSE_INVALID]
    client.close()


def test_live_transform_trajectory_has_exact_xyz_shape():
    evidence, action = fixture()
    def handler(request):
        return response(request, verdict="TRANSFORM", reason_codes=["TEST"],
                        authorized_action={"trajectory": [[0.0, 0.0]], "speed_mps": 0.1})
    client = GatekeeperClient("https://gatekeeper.test", transport=httpx.MockTransport(handler))
    decision = client.evaluate(evidence, action)
    assert decision.verdict == Verdict.HOLD
    assert decision.reason_codes[-1] == AUTHORIZED_ACTION_INVALID
    client.close()


def test_dispatch_guard_does_not_double_sample_wall_clock_per_check():
    calls = 0; now = 1_700_000_000_000
    def clock():
        nonlocal calls; calls += 1; return now
    evidence = EvidenceFrame.fresh(captured_at_ms=now); action = ProposedAction.pick_place(evidence.evidence_id)
    guard = DispatchGuard(clock_ms=clock)
    assert guard.check(evidence, action) is None and calls == 1


def test_reference_authority_rejects_future_evidence_without_execution_authority():
    evidence, action = fixture(); now = evidence.captured_at_ms - 1
    decision = ReferenceAuthorityEngine().evaluate(evidence, action, now_ms=now)
    assert decision.verdict == Verdict.HOLD and decision.authorized_action is None
    assert "EVIDENCE_IN_FUTURE" in decision.reason_codes
