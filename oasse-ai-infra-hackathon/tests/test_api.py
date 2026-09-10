import json
import unittest

import httpx
from fastapi.testclient import TestClient

from oasse_physical_ai import api
from oasse_physical_ai.gatekeeper_client import (
    AUTHORITY_UNAVAILABLE,
    AUTHORIZED_ACTION_MISSING,
    GatekeeperClient,
)
from oasse_physical_ai.models import EvidenceFrame, ProposedAction


def fake_gatekeeper(responder):
    return GatekeeperClient("https://gatekeeper.test", transport=httpx.MockTransport(responder))


def down(request):
    raise httpx.ConnectError("connection refused", request=request)


def transform_clamped(request):
    return httpx.Response(200, json={
        "decision_id": "gk-1",
        "verdict": "TRANSFORM",
        "reason_codes": ["SPEED_CLAMPED"],
        "authorized_action": {"speed_mps": 0.35},
        "policy_version": "gatekeeper-test-v1",
    })


def transform_without_action(request):
    return httpx.Response(200, json={"decision_id": "gk-2", "verdict": "TRANSFORM", "reason_codes": ["SPEED_CLAMPED"]})


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)

    def use_authority(self, authority):
        original = api.orchestrator.authority
        api.orchestrator.authority = authority
        self.addCleanup(setattr, api.orchestrator, "authority", original)

    def test_health_reports_reference_mode_by_default(self):
        body = self.client.get("/health").json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["authority_mode"], "reference")
        self.assertEqual(body["authority_engine"], "ReferenceAuthorityEngine")
        self.assertEqual(body["authority_mode_setting"], "reference")
        self.assertTrue(body["receipt_chain_valid"])

    def test_health_reports_live_mode_when_gatekeeper_client_is_wired(self):
        self.use_authority(fake_gatekeeper(down))
        body = self.client.get("/health").json()
        self.assertEqual(body["authority_mode"], "live")
        self.assertEqual(body["authority_engine"], "GatekeeperClient")

    def test_evaluate_fails_closed_when_gatekeeper_is_down(self):
        self.use_authority(fake_gatekeeper(down))
        ev = EvidenceFrame.fresh()
        action = ProposedAction.pick_place(ev.evidence_id)
        response = self.client.post("/v1/evaluate", json={"evidence": ev.__dict__, "action": action.__dict__})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["verdict"], "HOLD")
        self.assertEqual(body["reason_codes"], [AUTHORITY_UNAVAILABLE])
        self.assertIsNone(body["authorized_action"])

    def test_demo_overspeed_in_live_mode_executes_clamped_action(self):
        self.use_authority(fake_gatekeeper(transform_clamped))
        body = self.client.post("/v1/demo/overspeed").json()
        self.assertEqual(body["decision"]["verdict"], "TRANSFORM")
        self.assertTrue(body["executed"])
        self.assertEqual(body["decision"]["original_action"]["speed_mps"], 0.80)
        self.assertEqual(body["decision"]["authorized_action"]["speed_mps"], 0.35)
        self.assertEqual(body["actuator_result"]["speed_mps"], 0.35)
        self.assertIsNotNone(body["outcome_receipt"])

    def test_demo_overspeed_in_live_mode_holds_without_authorized_action(self):
        self.use_authority(fake_gatekeeper(transform_without_action))
        body = self.client.post("/v1/demo/overspeed").json()
        self.assertEqual(body["decision"]["verdict"], "HOLD")
        self.assertIn(AUTHORIZED_ACTION_MISSING, body["decision"]["reason_codes"])
        self.assertFalse(body["executed"])
        self.assertIsNone(body["outcome_receipt"])
        self.assertEqual(body["actuator_result"]["status"], "NOT_EXECUTED")

    def test_receipts_stay_valid_after_live_failures(self):
        self.use_authority(fake_gatekeeper(down))
        self.client.post("/v1/demo/allow")
        body = self.client.get("/v1/receipts").json()
        self.assertTrue(body["valid"])
        self.assertGreaterEqual(body["count"], 1)

    def test_unknown_scenario_is_404(self):
        self.assertEqual(self.client.post("/v1/demo/nope").status_code, 404)


if __name__ == "__main__":
    unittest.main()
