from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
import time
import uuid


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    TRANSFORM = "TRANSFORM"
    HOLD = "HOLD"
    DENY = "DENY"


@dataclass(frozen=True)
class EvidenceFrame:
    evidence_id: str
    captured_at_ms: int
    confidence: float
    workspace_clear: bool
    anomaly_score: float = 0.0
    target_label: str = "cube"
    camera_id: str = "camera-1"
    frame_hash: str = "demo-frame"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def fresh(**kwargs: Any) -> "EvidenceFrame":
        return EvidenceFrame(
            evidence_id=kwargs.pop("evidence_id", f"ev-{uuid.uuid4().hex[:10]}"),
            captured_at_ms=kwargs.pop("captured_at_ms", int(time.time() * 1000)),
            confidence=kwargs.pop("confidence", 0.99),
            workspace_clear=kwargs.pop("workspace_clear", True),
            **kwargs,
        )


@dataclass(frozen=True)
class ProposedAction:
    action_id: str
    actor_id: str
    action_type: str
    target_bin: str
    speed_mps: float
    evidence_id: str
    requested_at_ms: int
    object_id: str = "cube-1"
    trajectory: List[List[float]] = field(default_factory=lambda: [[0.0, 0.0, 0.0], [0.2, 0.0, 0.1]])
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def pick_place(evidence_id: str, **kwargs: Any) -> "ProposedAction":
        return ProposedAction(
            action_id=kwargs.pop("action_id", f"act-{uuid.uuid4().hex[:10]}"),
            actor_id=kwargs.pop("actor_id", "vla-planner-1"),
            action_type=kwargs.pop("action_type", "pick_place"),
            target_bin=kwargs.pop("target_bin", "accept"),
            speed_mps=kwargs.pop("speed_mps", 0.20),
            evidence_id=evidence_id,
            requested_at_ms=kwargs.pop("requested_at_ms", int(time.time() * 1000)),
            **kwargs,
        )


@dataclass
class AuthorityDecision:
    decision_id: str
    verdict: Verdict
    reason_codes: List[str]
    original_action: ProposedAction
    authorized_action: Optional[ProposedAction]
    evidence: EvidenceFrame
    evaluated_at_ms: int
    authority_latency_ms: float
    policy_version: str = "physical-ai-demo-v1"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["verdict"] = self.verdict.value
        return data


@dataclass
class Receipt:
    receipt_id: str
    receipt_type: str
    created_at_ms: int
    payload_hash: str
    prev_hash: str
    receipt_hash: str
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DispatchResult:
    decision: AuthorityDecision
    decision_receipt: Receipt
    executed: bool
    actuator_result: Dict[str, Any]
    outcome_receipt: Optional[Receipt]
    total_latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.to_dict(),
            "decision_receipt": self.decision_receipt.to_dict(),
            "executed": self.executed,
            "actuator_result": self.actuator_result,
            "outcome_receipt": self.outcome_receipt.to_dict() if self.outcome_receipt else None,
            "total_latency_ms": self.total_latency_ms,
        }
