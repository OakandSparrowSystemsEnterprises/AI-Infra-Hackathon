import time
import unittest
from dataclasses import replace

from oasse_physical_ai.models import EvidenceFrame, ProposedAction, Verdict
from oasse_physical_ai.policy import ReferenceAuthorityEngine


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.engine = ReferenceAuthorityEngine(evidence_max_age_ms=500, min_confidence=0.8, max_speed_mps=0.35)
        self.now = int(time.time() * 1000)
        self.ev = EvidenceFrame.fresh(captured_at_ms=self.now, confidence=0.99, workspace_clear=True)
        self.action = ProposedAction.pick_place(self.ev.evidence_id, speed_mps=0.2)

    def test_allow(self):
        self.assertEqual(self.engine.evaluate(self.ev, self.action, self.now).verdict, Verdict.ALLOW)

    def test_stale_holds(self):
        ev = replace(self.ev, captured_at_ms=self.now - 501)
        self.assertEqual(self.engine.evaluate(ev, self.action, self.now).verdict, Verdict.HOLD)

    def test_occupied_denies(self):
        ev = replace(self.ev, workspace_clear=False)
        self.assertEqual(self.engine.evaluate(ev, self.action, self.now).verdict, Verdict.DENY)

    def test_low_confidence_holds(self):
        ev = replace(self.ev, confidence=0.2)
        self.assertEqual(self.engine.evaluate(ev, self.action, self.now).verdict, Verdict.HOLD)

    def test_actor_denies(self):
        action = replace(self.action, actor_id="stranger")
        self.assertEqual(self.engine.evaluate(self.ev, action, self.now).verdict, Verdict.DENY)

    def test_evidence_binding_denies(self):
        action = replace(self.action, evidence_id="ev-other")
        self.assertEqual(self.engine.evaluate(self.ev, action, self.now).verdict, Verdict.DENY)

    def test_speed_transforms(self):
        action = replace(self.action, speed_mps=1.2)
        d = self.engine.evaluate(self.ev, action, self.now)
        self.assertEqual(d.verdict, Verdict.TRANSFORM)
        self.assertAlmostEqual(d.authorized_action.speed_mps, 0.35)

    def test_unknown_action_holds(self):
        action = replace(self.action, action_type="delete_robot")
        self.assertEqual(self.engine.evaluate(self.ev, action, self.now).verdict, Verdict.HOLD)

    def test_bad_target_denies(self):
        action = replace(self.action, target_bin="human")
        self.assertEqual(self.engine.evaluate(self.ev, action, self.now).verdict, Verdict.DENY)


if __name__ == "__main__":
    unittest.main()
