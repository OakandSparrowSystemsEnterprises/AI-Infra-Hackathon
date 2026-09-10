import unittest

from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine
from oasse_physical_ai.models import Verdict


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.o = PhysicalAIOrchestrator(ReferenceAuthorityEngine())

    def test_allow_executes(self):
        r = self.o.run("allow")
        self.assertEqual(r.decision.verdict, Verdict.ALLOW)
        self.assertTrue(r.executed)
        self.assertIsNotNone(r.outcome_receipt)

    def test_stale_does_not_execute(self):
        r = self.o.run("stale")
        self.assertEqual(r.decision.verdict, Verdict.HOLD)
        self.assertFalse(r.executed)
        self.assertIsNone(r.outcome_receipt)

    def test_occupied_does_not_execute(self):
        r = self.o.run("occupied")
        self.assertEqual(r.decision.verdict, Verdict.DENY)
        self.assertFalse(r.executed)

    def test_transform_executes_modified_action(self):
        r = self.o.run("overspeed")
        self.assertEqual(r.decision.verdict, Verdict.TRANSFORM)
        self.assertTrue(r.executed)
        self.assertLessEqual(r.actuator_result["speed_mps"], 0.35)

    def test_defect_routes_reject(self):
        r = self.o.run("defect")
        self.assertEqual(r.decision.verdict, Verdict.ALLOW)
        self.assertEqual(r.actuator_result["target_bin"], "reject")

    def test_chain_stays_valid_across_runs(self):
        for s in ["allow", "stale", "occupied", "overspeed", "defect"]:
            self.o.run(s)
        self.assertTrue(self.o.receipts.verify())


if __name__ == "__main__":
    unittest.main()
