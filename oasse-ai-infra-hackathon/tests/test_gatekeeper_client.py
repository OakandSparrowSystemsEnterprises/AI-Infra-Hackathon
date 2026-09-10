"""Live-mode boundary tests for GatekeeperClient.

A fake Gatekeeper service is wired in through httpx.MockTransport, so no
network is involved and no proprietary service is needed.
"""
import json
import os
import unittest
from dataclasses import replace
from unittest import mock

import httpx

from oasse_physical_ai import gatekeeper_client as gc
from oasse_physical_ai.gatekeeper_client import (
    GatekeeperClient,
    build_authority_client,
    configured_authority_mode,
    describe_authority,
)
from oasse_physical_ai.models import AuthorityDecision, EvidenceFrame, ProposedAction, Verdict
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator, executable
from oasse_physical_ai.policy import ReferenceAuthorityEngine

ORIGINAL_SPEED = 0.80  # what MockVLAProvider proposes for the "overspeed" scenario
ALLOW_SPEED = 0.20  # what it proposes for every other scenario
CLAMPED_SPEED = 0.35


class RecordingActuator:
    """Stand-in actuator that records every action it is asked to execute."""

    def __init__(self):
        self.calls = []

    def execute(self, action):
        self.calls.append(action)
        return {
            "status": "EXECUTED",
            "action_id": action.action_id,
            "object_id": action.object_id,
            "target_bin": action.target_bin,
            "speed_mps": action.speed_mps,
            "trajectory_points": len(action.trajectory),
        }


def live_client(responder):
    return GatekeeperClient("https://gatekeeper.test", token="test-token", transport=httpx.MockTransport(responder))


def live_orchestrator(responder):
    orch = PhysicalAIOrchestrator(live_client(responder))
    orch.actuator = RecordingActuator()
    return orch


def verdict_service(verdict, authorized=None, **overrides):
    """A fake Gatekeeper that answers every evaluation with `verdict`.

    `authorized` is a callable taking the submitted action dict and returning
    the `authorized_action` payload to send back; None omits the field.
    """

    def responder(request):
        payload = json.loads(request.content)
        body = {
            "decision_id": "gk-decision-1",
            "verdict": verdict,
            "reason_codes": ["SPEED_CLAMPED"] if verdict == "TRANSFORM" else ["POLICY_SATISFIED"],
            "evaluated_at_ms": 1_700_000_000_000,
            "authority_latency_ms": 0.42,
            "policy_version": "gatekeeper-test-v1",
        }
        body.update(overrides)
        if authorized is not None:
            body["authorized_action"] = authorized(payload["action"])
        return httpx.Response(200, json=body)

    return responder


def raw_service(content, status=200):
    """A fake Gatekeeper that returns exactly these bytes."""
    return lambda request: httpx.Response(status, content=content, headers={"Content-Type": "application/json"})


def down(request):
    raise httpx.ConnectError("connection refused", request=request)


def slow(request):
    raise httpx.ReadTimeout("no response within timeout", request=request)


def http_503(request):
    return httpx.Response(503, text="upstream unavailable")


def not_json(request):
    return httpx.Response(200, content=b"<html>maintenance</html>")


DEEPLY_NESTED = b"[" * 200_000 + b"]" * 200_000
OVERFLOW_TIMESTAMP = b'{"decision_id": "d", "verdict": "ALLOW", "evaluated_at_ms": 1e999}'
NAN_LATENCY = b'{"decision_id": "d", "verdict": "ALLOW", "authority_latency_ms": NaN}'


class HeldWithoutExecution:
    """Mixin assertions for decisions the adapter refused to execute."""

    def assert_held(self, orch, result, code, upstream):
        self.assertEqual(result.decision.verdict, Verdict.HOLD)
        self.assertEqual(result.decision.reason_codes, [upstream, code])  # upstream reason codes are preserved
        self.assertIsNone(result.decision.authorized_action)
        self.assertFalse(result.executed)
        self.assertEqual(orch.actuator.calls, [])
        self.assertIsNone(result.outcome_receipt)
        self.assertEqual(result.actuator_result["status"], "NOT_EXECUTED")
        self.assertEqual(len(orch.receipts.all()), 1)  # the decision receipt is still sealed
        self.assertEqual(orch.receipts.all()[0].payload["verdict"], "HOLD")
        self.assertTrue(orch.receipts.verify())
        self.assertEqual(result.decision.decision_id, "gk-decision-1")
        self.assertEqual(result.decision.policy_version, "gatekeeper-test-v1")


class LiveTransformTests(HeldWithoutExecution, unittest.TestCase):
    def test_transform_executes_returned_action_not_original(self):
        orch = live_orchestrator(verdict_service("TRANSFORM", authorized=lambda a: {**a, "speed_mps": CLAMPED_SPEED}))
        r = orch.run("overspeed")
        self.assertEqual(r.decision.verdict, Verdict.TRANSFORM)
        self.assertTrue(r.executed)
        self.assertEqual([call.speed_mps for call in orch.actuator.calls], [CLAMPED_SPEED])
        self.assertEqual(r.decision.original_action.speed_mps, ORIGINAL_SPEED)
        self.assertEqual(r.decision.authorized_action.speed_mps, CLAMPED_SPEED)
        self.assertEqual(r.decision.authorized_action.action_id, r.decision.original_action.action_id)
        self.assertEqual(r.decision.authorized_action.evidence_id, r.decision.original_action.evidence_id)
        self.assertEqual(r.decision_receipt.payload["original_action"]["speed_mps"], ORIGINAL_SPEED)
        self.assertEqual(r.decision_receipt.payload["authorized_action"]["speed_mps"], CLAMPED_SPEED)
        self.assertIsNotNone(r.outcome_receipt)
        self.assertEqual(r.decision.policy_version, "gatekeeper-test-v1")
        self.assertTrue(orch.receipts.verify())

    def test_transform_accepts_changed_fields_only(self):
        orch = live_orchestrator(verdict_service("TRANSFORM", authorized=lambda a: {"speed_mps": CLAMPED_SPEED}))
        r = orch.run("overspeed")
        self.assertTrue(r.executed)
        self.assertEqual([call.speed_mps for call in orch.actuator.calls], [CLAMPED_SPEED])
        self.assertEqual(r.decision.authorized_action.action_id, r.decision.original_action.action_id)

    def test_transform_ignores_unknown_fields(self):
        orch = live_orchestrator(
            verdict_service("TRANSFORM", authorized=lambda a: {"speed_mps": CLAMPED_SPEED, "transform_notes": "clamped"})
        )
        r = orch.run("overspeed")
        self.assertTrue(r.executed)
        self.assertEqual(orch.actuator.calls[0].speed_mps, CLAMPED_SPEED)

    def test_transform_may_change_other_physical_fields(self):
        """Gatekeeper may transform something other than speed; the returned action is what executes."""
        orch = live_orchestrator(verdict_service("TRANSFORM", authorized=lambda a: {"target_bin": "reject"}))
        r = orch.run("allow")
        self.assertTrue(r.executed)
        self.assertEqual(orch.actuator.calls[0].target_bin, "reject")
        self.assertEqual(orch.actuator.calls[0].speed_mps, ALLOW_SPEED)
        self.assertEqual(r.decision.original_action.target_bin, "accept")

    def test_transform_without_authorized_action_holds(self):
        for responder in (verdict_service("TRANSFORM"), verdict_service("TRANSFORM", authorized=lambda a: None)):
            orch = live_orchestrator(responder)
            self.assert_held(orch, orch.run("overspeed"), gc.AUTHORIZED_ACTION_MISSING, "SPEED_CLAMPED")

    def test_transform_without_physical_change_holds(self):
        cosmetic = (
            lambda a: dict(a),
            lambda a: {},
            lambda a: {"speed_mps": ORIGINAL_SPEED},
            lambda a: {"speed_mps": ORIGINAL_SPEED + 2e-16},  # floating-point noise is not a transform
            lambda a: {"metadata": {"note": "clamped"}},
            lambda a: {"requested_at_ms": 1},
            lambda a: {**a, "metadata": {}, "requested_at_ms": 5},
        )
        for authorized in cosmetic:
            orch = live_orchestrator(verdict_service("TRANSFORM", authorized=authorized))
            self.assert_held(orch, orch.run("overspeed"), gc.AUTHORIZED_ACTION_UNCHANGED, "SPEED_CLAMPED")

    def test_transform_rebound_to_other_identity_holds(self):
        for name in ("action_id", "actor_id", "evidence_id"):
            orch = live_orchestrator(
                verdict_service("TRANSFORM", authorized=lambda a, n=name: {**a, "speed_mps": CLAMPED_SPEED, n: "somewhere-else"})
            )
            self.assert_held(orch, orch.run("overspeed"), gc.AUTHORIZED_ACTION_BINDING_MISMATCH, "SPEED_CLAMPED")

    def test_transform_with_unusable_authorized_action_holds(self):
        unusable = (
            "fast",
            42,
            ["speed_mps", CLAMPED_SPEED],
            {"speed_mps": "fast"},
            {"speed_mps": "0.35"},  # numbers must be numbers
            {"speed_mps": "1e3"},
            {"speed_mps": None},
            {"speed_mps": True},  # bool is not a speed
            {"speed_mps": False},
            {"speed_mps": -0.1},
            {"speed_mps": CLAMPED_SPEED, "trajectory": None},
            {"speed_mps": CLAMPED_SPEED, "trajectory": 42},
            {"speed_mps": CLAMPED_SPEED, "trajectory": "abc"},
            {"speed_mps": CLAMPED_SPEED, "trajectory": []},
            {"speed_mps": CLAMPED_SPEED, "trajectory": [[]]},
            {"speed_mps": CLAMPED_SPEED, "trajectory": [[0.0, "a", 0.0]]},
            {"speed_mps": CLAMPED_SPEED, "trajectory": [[0.0, True, 0.0]]},
            {"speed_mps": CLAMPED_SPEED, "target_bin": 123},
            {"speed_mps": CLAMPED_SPEED, "target_bin": ""},
            {"speed_mps": CLAMPED_SPEED, "object_id": {"a": 1}},
            {"speed_mps": CLAMPED_SPEED, "metadata": "x"},
            {"speed_mps": CLAMPED_SPEED, "action_type": None},
            {"speed_mps": CLAMPED_SPEED, "requested_at_ms": True},
            {"speed_mps": CLAMPED_SPEED, "requested_at_ms": -1},
        )
        for bad in unusable:
            orch = live_orchestrator(verdict_service("TRANSFORM", authorized=lambda a, b=bad: b))
            self.assert_held(orch, orch.run("overspeed"), gc.AUTHORIZED_ACTION_INVALID, "SPEED_CLAMPED")

    def test_non_finite_speed_in_authorized_action_holds(self):
        for token in (b"NaN", b"Infinity", b"-Infinity"):
            body = b'{"decision_id": "gk-decision-1", "verdict": "TRANSFORM", "reason_codes": ["SPEED_CLAMPED"], "policy_version": "gatekeeper-test-v1", "authorized_action": {"speed_mps": ' + token + b"}}"
            orch = live_orchestrator(raw_service(body))
            self.assert_held(orch, orch.run("overspeed"), gc.AUTHORIZED_ACTION_INVALID, "SPEED_CLAMPED")

    def test_original_speed_never_reaches_actuator_in_live_mode(self):
        """Whatever a non-ALLOW response looks like, the overspeed proposal is never executed as proposed.

        The actuator only ever receives an action the service actually returned
        that differs from the proposal in a physical field. Every responder here
        either authorizes the clamped speed or must end in a HOLD.
        """
        responders = [
            verdict_service("TRANSFORM", authorized=lambda a: {**a, "speed_mps": CLAMPED_SPEED}),
            verdict_service("TRANSFORM", authorized=lambda a: {"speed_mps": CLAMPED_SPEED}),
            verdict_service("TRANSFORM"),
            verdict_service("TRANSFORM", authorized=lambda a: None),
            verdict_service("TRANSFORM", authorized=lambda a: dict(a)),
            verdict_service("TRANSFORM", authorized=lambda a: {"speed_mps": ORIGINAL_SPEED}),
            verdict_service("TRANSFORM", authorized=lambda a: {"speed_mps": ORIGINAL_SPEED + 2e-16}),
            verdict_service("TRANSFORM", authorized=lambda a: {"metadata": {"note": "x"}}),
            verdict_service("TRANSFORM", authorized=lambda a: {"requested_at_ms": 1}),
            verdict_service("TRANSFORM", authorized=lambda a: {**a, "speed_mps": CLAMPED_SPEED, "action_id": "act-other"}),
            verdict_service("TRANSFORM", authorized=lambda a: "fast"),
            verdict_service("TRANSFORM", authorized=lambda a: {"speed_mps": "fast"}),
            verdict_service("TRANSFORM", authorized=lambda a: {"speed_mps": True}),
            verdict_service("TRANSFORM", authorized=lambda a: {"speed_mps": CLAMPED_SPEED, "trajectory": None}),
            verdict_service("ALLOW", authorized=lambda a: {"speed_mps": CLAMPED_SPEED}),  # contradictory ALLOW
            verdict_service("HOLD"),
            verdict_service("DENY"),
            verdict_service("TRANSFORM", reason_codes=None),
            verdict_service("TRANSFORM", reason_codes="SPEED_CLAMPED"),
            verdict_service("TRANSFORM", decision_id=None),
            verdict_service("TRANSFORM", decision_id=""),
            verdict_service("TRANSFORM", authority_latency_ms=-1),
            down,
            slow,
            http_503,
            not_json,
            raw_service(b"null"),
            raw_service(b""),
            raw_service(DEEPLY_NESTED),
            raw_service(OVERFLOW_TIMESTAMP),
            raw_service(NAN_LATENCY),
            lambda request: httpx.Response(200, json={"verdict": "TRANSFORM"}),
            lambda request: httpx.Response(200, json=[]),
        ]
        for responder in responders:
            orch = live_orchestrator(responder)
            r = orch.run("overspeed")
            self.assertEqual(r.decision.original_action.speed_mps, ORIGINAL_SPEED)
            for call in orch.actuator.calls:
                self.assertNotEqual(call.speed_mps, ORIGINAL_SPEED)
                self.assertLessEqual(call.speed_mps, CLAMPED_SPEED)
            if r.executed:
                self.assertEqual(r.decision.verdict, Verdict.TRANSFORM)
                self.assertEqual([call.speed_mps for call in orch.actuator.calls], [CLAMPED_SPEED])
            else:
                self.assertEqual(orch.actuator.calls, [])
                self.assertIsNone(r.outcome_receipt)
            self.assertEqual(len(orch.receipts.all()), 2 if r.executed else 1)
            self.assertTrue(orch.receipts.verify())


class LiveVerdictTests(HeldWithoutExecution, unittest.TestCase):
    def test_allow_executes_proposal_as_authorized(self):
        orch = live_orchestrator(verdict_service("ALLOW"))
        r = orch.run("allow")
        self.assertEqual(r.decision.verdict, Verdict.ALLOW)
        self.assertTrue(r.executed)
        self.assertEqual(r.decision.authorized_action, r.decision.original_action)
        self.assertEqual(orch.actuator.calls, [r.decision.original_action])
        self.assertEqual(r.decision.reason_codes, ["POLICY_SATISFIED"])
        self.assertEqual(r.decision.authority_latency_ms, 0.42)
        self.assertEqual(r.decision.evaluated_at_ms, 1_700_000_000_000)

    def test_allow_with_matching_authorized_action_executes(self):
        for authorized in (lambda a: dict(a), lambda a: {"speed_mps": ALLOW_SPEED}, lambda a: {"metadata": {"seen": True}}):
            orch = live_orchestrator(verdict_service("ALLOW", authorized=authorized))
            r = orch.run("allow")
            self.assertTrue(r.executed)
            self.assertEqual(orch.actuator.calls, [r.decision.original_action])

    def test_allow_with_contradictory_authorized_action_holds(self):
        for authorized in (lambda a: {"speed_mps": CLAMPED_SPEED}, lambda a: {"target_bin": "reject"}, lambda a: {**a, "object_id": "cube-2"}):
            orch = live_orchestrator(verdict_service("ALLOW", authorized=authorized))
            self.assert_held(orch, orch.run("overspeed"), gc.AUTHORIZED_ACTION_CONFLICT, "POLICY_SATISFIED")

    def test_allow_with_unusable_or_rebound_authorized_action_holds(self):
        orch = live_orchestrator(verdict_service("ALLOW", authorized=lambda a: {"speed_mps": "fast"}))
        self.assert_held(orch, orch.run("allow"), gc.AUTHORIZED_ACTION_INVALID, "POLICY_SATISFIED")
        orch = live_orchestrator(verdict_service("ALLOW", authorized=lambda a: {"action_id": "act-other"}))
        self.assert_held(orch, orch.run("allow"), gc.AUTHORIZED_ACTION_BINDING_MISMATCH, "POLICY_SATISFIED")

    def test_hold_and_deny_do_not_execute(self):
        for verdict in ("HOLD", "DENY"):
            orch = live_orchestrator(verdict_service(verdict, authorized=lambda a: {"speed_mps": CLAMPED_SPEED}))
            r = orch.run("allow")
            self.assertEqual(r.decision.verdict, Verdict(verdict))
            self.assertIsNone(r.decision.authorized_action)
            self.assertFalse(r.executed)
            self.assertEqual(orch.actuator.calls, [])

    def test_request_carries_token_and_bound_payload(self):
        seen = {}

        def responder(request):
            seen["url"] = str(request.url)
            seen["auth"] = request.headers.get("Authorization")
            seen["content_type"] = request.headers.get("Content-Type")
            seen["payload"] = json.loads(request.content)
            return verdict_service("ALLOW")(request)

        orch = live_orchestrator(responder)
        r = orch.run("allow")
        self.assertEqual(seen["url"], "https://gatekeeper.test/v1/evaluate")
        self.assertEqual(seen["auth"], "Bearer test-token")
        self.assertEqual(seen["content_type"], "application/json")
        self.assertEqual(seen["payload"]["action"]["evidence_id"], seen["payload"]["evidence"]["evidence_id"])
        self.assertEqual(seen["payload"]["action"]["action_id"], r.decision.original_action.action_id)

    def test_optional_fields_default_when_null_or_absent(self):
        ev = EvidenceFrame.fresh()
        action = ProposedAction.pick_place(ev.evidence_id)
        absent = {"decision_id": "d", "verdict": "ALLOW"}
        nulls = {**absent, "reason_codes": None, "evaluated_at_ms": None, "authority_latency_ms": None, "policy_version": None, "authorized_action": None}
        for body in (absent, nulls):
            d = live_client(lambda request, b=body: httpx.Response(200, json=b)).evaluate(ev, action)
            self.assertEqual(d.verdict, Verdict.ALLOW)
            self.assertEqual(d.reason_codes, [])
            self.assertGreater(d.evaluated_at_ms, 0)
            self.assertEqual(d.authority_latency_ms, 0.0)
            self.assertEqual(d.policy_version, gc.LIVE_POLICY_VERSION_DEFAULT)


class LiveFailureTests(unittest.TestCase):
    def assert_failed_closed(self, orch, result, codes):
        self.assertEqual(result.decision.verdict, Verdict.HOLD)
        self.assertEqual(result.decision.reason_codes, codes)
        self.assertIsNone(result.decision.authorized_action)
        self.assertFalse(result.executed)
        self.assertEqual(orch.actuator.calls, [])
        self.assertIsNone(result.outcome_receipt)
        self.assertEqual(result.actuator_result, {"status": "NOT_EXECUTED", "reason": "HOLD"})
        self.assertEqual(result.decision.policy_version, gc.LIVE_UNAVAILABLE_POLICY_VERSION)
        self.assertEqual(result.decision.decision_id, f"dec-{result.decision.original_action.action_id}")
        self.assertGreaterEqual(result.decision.authority_latency_ms, 0.0)
        receipts = orch.receipts.all()
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0].receipt_type, "AUTHORITY_DECISION")
        self.assertEqual(receipts[0].payload["verdict"], "HOLD")
        self.assertEqual(receipts[0].payload["reason_codes"], codes)
        self.assertTrue(orch.receipts.verify())
        self.assertEqual(orch.metrics.snapshot()["verdict_counts"], {"HOLD": 1})

    def test_transport_error_fails_closed(self):
        orch = live_orchestrator(down)
        self.assert_failed_closed(orch, orch.run("allow"), [gc.AUTHORITY_UNAVAILABLE])

    def test_timeout_fails_closed(self):
        orch = live_orchestrator(slow)
        self.assert_failed_closed(orch, orch.run("allow"), [gc.AUTHORITY_UNAVAILABLE])

    def test_http_error_fails_closed(self):
        orch = live_orchestrator(http_503)
        self.assert_failed_closed(orch, orch.run("allow"), [gc.AUTHORITY_UNAVAILABLE, "HTTP_503"])

    def test_client_construction_failure_fails_closed(self):
        orch = live_orchestrator(verdict_service("ALLOW"))
        with mock.patch.object(gc.httpx, "Client", side_effect=ImportError("socksio is not installed")):
            r = orch.run("allow")
        self.assert_failed_closed(orch, r, [gc.AUTHORITY_UNAVAILABLE])

    def test_unserializable_request_fails_closed(self):
        ev = EvidenceFrame.fresh(metadata={"mask": {1, 2, 3}})  # a set is not JSON
        client = live_client(verdict_service("ALLOW"))
        d = client.evaluate(ev, ProposedAction.pick_place(ev.evidence_id))
        self.assertEqual((d.verdict, d.reason_codes), (Verdict.HOLD, [gc.AUTHORITY_REQUEST_INVALID]))
        ev = EvidenceFrame.fresh()
        d = client.evaluate(ev, ProposedAction.pick_place(ev.evidence_id, speed_mps=float("nan")))
        self.assertEqual((d.verdict, d.reason_codes), (Verdict.HOLD, [gc.AUTHORITY_REQUEST_INVALID]))

    def test_non_json_body_fails_closed(self):
        orch = live_orchestrator(not_json)
        self.assert_failed_closed(orch, orch.run("allow"), [gc.AUTHORITY_RESPONSE_INVALID])

    def test_malformed_body_fails_closed(self):
        bodies = [
            {"verdict": "ALLOW"},  # no decision_id
            {"decision_id": "d"},  # no verdict
            {"decision_id": "d", "verdict": "MAYBE"},
            {"decision_id": "d", "verdict": "allow"},
            {"decision_id": "d", "verdict": 5},
            {"decision_id": None, "verdict": "ALLOW"},
            {"decision_id": "", "verdict": "ALLOW"},
            {"decision_id": 7, "verdict": "ALLOW"},
            {"decision_id": "d", "verdict": "ALLOW", "reason_codes": "SPEED_CLAMPED"},
            {"decision_id": "d", "verdict": "ALLOW", "reason_codes": {"a": 1}},
            {"decision_id": "d", "verdict": "ALLOW", "reason_codes": [1]},
            {"decision_id": "d", "verdict": "ALLOW", "authority_latency_ms": "fast"},
            {"decision_id": "d", "verdict": "ALLOW", "authority_latency_ms": -5},
            {"decision_id": "d", "verdict": "ALLOW", "authority_latency_ms": True},
            {"decision_id": "d", "verdict": "ALLOW", "evaluated_at_ms": "now"},
            {"decision_id": "d", "verdict": "ALLOW", "evaluated_at_ms": -1},
            {"decision_id": "d", "verdict": "ALLOW", "policy_version": ""},
            {"decision_id": "d", "verdict": "ALLOW", "policy_version": 3},
            [],
            "ALLOW",
            42,
        ]
        for body in bodies:
            orch = live_orchestrator(lambda request, b=body: httpx.Response(200, json=b))
            self.assert_failed_closed(orch, orch.run("allow"), [gc.AUTHORITY_RESPONSE_INVALID])
        for content in (b"null", b"", b"{", DEEPLY_NESTED, OVERFLOW_TIMESTAMP, NAN_LATENCY):
            orch = live_orchestrator(raw_service(content))
            self.assert_failed_closed(orch, orch.run("allow"), [gc.AUTHORITY_RESPONSE_INVALID])

    def test_evaluate_never_raises(self):
        ev = EvidenceFrame.fresh()
        action = ProposedAction.pick_place(ev.evidence_id)
        responders = (down, slow, http_503, not_json, raw_service(b""), raw_service(DEEPLY_NESTED),
                      raw_service(OVERFLOW_TIMESTAMP), lambda request: httpx.Response(200, json=[]))
        for responder in responders:
            d = live_client(responder).evaluate(ev, action)
            self.assertIsInstance(d, AuthorityDecision)
            self.assertEqual(d.verdict, Verdict.HOLD)
            self.assertIsNone(d.authorized_action)
        with mock.patch.object(gc.httpx, "Client", side_effect=RuntimeError("boom")):
            d = live_client(down).evaluate(ev, action)
        self.assertEqual((d.verdict, d.reason_codes), (Verdict.HOLD, [gc.AUTHORITY_UNAVAILABLE]))

    def test_chain_survives_an_outage_between_healthy_runs(self):
        orch = live_orchestrator(verdict_service("ALLOW"))
        first = orch.run("allow")
        orch.authority = live_client(down)
        outage = orch.run("allow")
        orch.authority = live_client(verdict_service("ALLOW"))
        third = orch.run("allow")
        self.assertTrue(first.executed)
        self.assertFalse(outage.executed)
        self.assertTrue(third.executed)
        self.assertEqual(len(orch.receipts.all()), 5)  # 3 decisions + 2 outcomes
        self.assertEqual(outage.decision_receipt.prev_hash, first.outcome_receipt.receipt_hash)
        self.assertEqual(third.decision_receipt.prev_hash, outage.decision_receipt.receipt_hash)
        self.assertTrue(orch.receipts.verify())


class ExecutionGateTests(unittest.TestCase):
    """The orchestrator's last gate before the actuator, independent of the engine."""

    def make_decision(self, verdict, authorized):
        ev = EvidenceFrame.fresh()
        action = ProposedAction.pick_place(ev.evidence_id, speed_mps=ORIGINAL_SPEED)
        auth = None if authorized is None else (action if authorized == "same" else authorized(action))
        return AuthorityDecision("dec-1", verdict, [], action, auth, ev, 0, 0.0)

    def test_transform_with_unchanged_action_is_not_executable(self):
        self.assertFalse(executable(self.make_decision(Verdict.TRANSFORM, "same")))
        self.assertFalse(executable(self.make_decision(Verdict.TRANSFORM, None)))
        self.assertTrue(executable(self.make_decision(Verdict.TRANSFORM, lambda a: replace(a, speed_mps=CLAMPED_SPEED))))
        self.assertTrue(executable(self.make_decision(Verdict.ALLOW, "same")))
        self.assertFalse(executable(self.make_decision(Verdict.HOLD, None)))
        self.assertFalse(executable(self.make_decision(Verdict.DENY, None)))

    def test_orchestrator_refuses_unchanged_transform_from_any_engine(self):
        class EchoingTransformEngine:
            def evaluate(self, evidence, action):
                return AuthorityDecision("dec-echo", Verdict.TRANSFORM, ["SPEED_CLAMPED"], action, action, evidence, 0, 0.0)

        class EmptyTransformEngine:
            def evaluate(self, evidence, action):
                return AuthorityDecision("dec-empty", Verdict.TRANSFORM, ["SPEED_CLAMPED"], action, None, evidence, 0, 0.0)

        for engine, reason in ((EchoingTransformEngine(), "TRANSFORM_WITHOUT_AUTHORIZED_CHANGE"),
                               (EmptyTransformEngine(), "TRANSFORM_WITHOUT_AUTHORIZED_ACTION")):
            orch = PhysicalAIOrchestrator(engine)
            orch.actuator = RecordingActuator()
            r = orch.run("overspeed")
            self.assertFalse(r.executed)
            self.assertEqual(orch.actuator.calls, [])
            self.assertEqual(r.actuator_result, {"status": "NOT_EXECUTED", "reason": reason})
            self.assertIsNone(r.outcome_receipt)
            self.assertTrue(orch.receipts.verify())

    def test_reference_engine_transform_still_executes_clamped_action(self):
        orch = PhysicalAIOrchestrator(ReferenceAuthorityEngine())
        orch.actuator = RecordingActuator()
        r = orch.run("overspeed")
        self.assertTrue(r.executed)
        self.assertEqual([call.speed_mps for call in orch.actuator.calls], [CLAMPED_SPEED])


class AuthorityModeTests(unittest.TestCase):
    def test_describe_reference_engine(self):
        self.assertEqual(
            describe_authority(ReferenceAuthorityEngine()),
            {"authority_mode": "reference", "authority_engine": "ReferenceAuthorityEngine"},
        )

    def test_describe_live_client(self):
        self.assertEqual(
            describe_authority(live_client(down)),
            {"authority_mode": "live", "authority_engine": "GatekeeperClient"},
        )

    def test_describe_custom_engine(self):
        class Custom:
            def evaluate(self, evidence, action):
                raise NotImplementedError

        self.assertEqual(describe_authority(Custom()), {"authority_mode": "custom", "authority_engine": "Custom"})

    def test_build_defaults_to_reference(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsInstance(build_authority_client(), ReferenceAuthorityEngine)
            self.assertEqual(configured_authority_mode(), "reference")

    def test_build_live_is_case_insensitive(self):
        with mock.patch.dict(os.environ, {"AUTHORITY_MODE": " Live ", "GATEKEEPER_URL": "https://gatekeeper.test/"}, clear=True):
            client = build_authority_client()
            self.assertIsInstance(client, GatekeeperClient)
            self.assertEqual(client.base_url, "https://gatekeeper.test")
            self.assertEqual(configured_authority_mode(), "live")

    def test_unknown_setting_falls_back_to_reference_but_is_reported(self):
        with mock.patch.dict(os.environ, {"AUTHORITY_MODE": "prod"}, clear=True):
            self.assertIsInstance(build_authority_client(), ReferenceAuthorityEngine)
            self.assertEqual(configured_authority_mode(), "prod")

    def test_live_without_url_is_a_configuration_error(self):
        with mock.patch.dict(os.environ, {"AUTHORITY_MODE": "live"}, clear=True):
            with self.assertRaises(ValueError):
                build_authority_client()


if __name__ == "__main__":
    unittest.main()
