from __future__ import annotations

from typing import Dict
from ..models import ProposedAction


class SimulatedActuator:
    def execute(self, action: ProposedAction) -> Dict[str, object]:
        return {
            "status": "EXECUTED",
            "action_id": action.action_id,
            "object_id": action.object_id,
            "target_bin": action.target_bin,
            "speed_mps": action.speed_mps,
            "trajectory_points": len(action.trajectory),
        }
