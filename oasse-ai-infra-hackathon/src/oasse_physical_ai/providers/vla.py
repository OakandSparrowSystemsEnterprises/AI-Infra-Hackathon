from __future__ import annotations

from ..models import EvidenceFrame, ProposedAction


class MockVLAProvider:
    def propose(self, evidence: EvidenceFrame, scenario: str = "allow") -> ProposedAction:
        target = "reject" if evidence.anomaly_score >= 0.80 else "accept"
        speed = 0.80 if scenario == "overspeed" else 0.20
        actor = "unknown-agent" if scenario == "identity_mismatch" else "vla-planner-1"
        ev_id = "wrong-evidence" if scenario == "binding_mismatch" else evidence.evidence_id
        return ProposedAction.pick_place(
            ev_id,
            target_bin=target,
            speed_mps=speed,
            actor_id=actor,
            metadata={"planner": "mock-vla", "source_anomaly_score": evidence.anomaly_score},
        )
