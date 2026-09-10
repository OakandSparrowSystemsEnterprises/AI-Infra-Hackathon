from __future__ import annotations

"""On-site adapter seam for Intel/OpenVINO physical AI integration.

The hackathon shell keeps this dependency optional so CI runs without robot
hardware. Replace the methods below with the event-provided camera, VLA, and
SO-101 bindings while preserving the EvidenceFrame and ProposedAction contracts.
"""

from ..models import EvidenceFrame, ProposedAction


class OpenVINOPhysicalAIAdapter:
    def observe(self) -> EvidenceFrame:
        raise NotImplementedError("Bind Intel camera/perception pipeline on site")

    def propose(self, evidence: EvidenceFrame) -> ProposedAction:
        raise NotImplementedError("Bind Physical AI Studio / VLA model on site")

    def execute(self, action: ProposedAction) -> dict:
        raise NotImplementedError("Bind SO-101 actuator API on site")
