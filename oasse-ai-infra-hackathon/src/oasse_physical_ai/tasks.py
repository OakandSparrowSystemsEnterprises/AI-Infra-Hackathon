"""One-shot inspection tasks: authorized motion is not proof of task completion."""
from __future__ import annotations

import threading
import time
import uuid
from typing import Callable, Mapping, Any

from .dispatch import copy_action
from .models import ProposedAction, Verdict
from .normalization import plain, integer, number, text
from .orchestrator import PhysicalAIOrchestrator

Postcondition = Callable[[ProposedAction], Mapping[str, Any]]


class InspectionTask:
    """Run once, stop on ambiguity, and seal a separate postcondition record.

    Repeating run() returns the recorded result, never retries a physical effect.
    The verifier must make a NEW observation; it must not echo a command ACK.
    """

    def __init__(self, orchestrator: PhysicalAIOrchestrator, verify: Postcondition,
                 *, task_id: str | None = None, max_settled_speed_mps: float = .01) -> None:
        self.orchestrator = orchestrator
        self.verify = verify
        self.task_id = text(task_id or "task-" + uuid.uuid4().hex, "task_id")
        self.max_settled_speed_mps = number(max_settled_speed_mps, "max_settled_speed_mps", minimum=0)
        self._result: dict | None = None
        self._started = False
        self._lock = threading.RLock()

    def run(self, scenario: str = "allow") -> dict:
        with self._lock:
            if self._result is not None:
                return plain(self._result, max_nodes=100000)
            if self._started:
                raise RuntimeError("TASK_RUN_INTERRUPTED_NO_AUTOMATIC_RETRY")
            self._started = True
            # Serialize the task with all uses of this orchestrator, including verification.
            with self.orchestrator._lock:
                result = self.orchestrator.run(scenario)
                status = "UNKNOWN" if result.dispatch_attempted else "HELD"
                if not result.dispatch_attempted and result.decision.verdict == Verdict.DENY:
                    status = "DENIED"
                verification: dict = {"verified": False, "reason": "NO_CONFIRMED_EXECUTION"}
                if result.executed:
                    before = int(time.time() * 1000)
                    try:
                        authorized = copy_action(result.decision.authorized_action)
                        observation = plain(self.verify(authorized))
                        after = int(time.time() * 1000)
                        if not isinstance(observation, dict):
                            raise TypeError("postcondition must be an object")
                        when = integer(observation["observed_at_ms"], "observed_at_ms")
                        if not before <= when <= after:
                            raise ValueError("verification must use a new observation")
                        text(observation["observation_source"], "observation_source")
                        if observation["object_id"] != authorized.object_id:
                            raise ValueError("verification object mismatch")
                        measured = number(observation["object_speed_mps"], "object_speed_mps", minimum=0)
                        confirmed = (observation.get("observed_bin") == authorized.target_bin
                                     and observation.get("object_released") is True
                                     and measured <= self.max_settled_speed_mps)
                        status = "COMPLETE" if confirmed else "POSTCONDITION_FAILED"
                        if authorized.target_bin != result.decision.original_action.target_bin:
                            status = "ROUTE_CHANGED"
                        verification = {"verified": status == "COMPLETE", "observation": observation,
                                        "reason": status}
                    except Exception as exc:
                        status = "UNKNOWN"
                        verification = {"verified": False, "reason": "POSTCONDITION_UNAVAILABLE",
                                        "error_type": type(exc).__name__}
                task_record = {"task_id": self.task_id, "status": status,
                    "task_complete": status == "COMPLETE", "dispatch_attempted": result.dispatch_attempted,
                    "execution_confirmed": result.executed,
                    "decision_receipt_hash": result.decision_receipt.receipt_hash,
                    "outcome_receipt_hash": result.outcome_receipt.receipt_hash if result.outcome_receipt else None,
                    "requested_bin": result.decision.original_action.target_bin,
                    "authorized_bin": result.decision.authorized_action.target_bin if result.decision.authorized_action else None,
                    "verification": verification}
                self.orchestrator._check_chain()
                receipt = self.orchestrator.receipts.seal("TASK_VERIFICATION", task_record)
                self._result = {**task_record, "task_receipt_hash": receipt.receipt_hash,
                                "dispatch": result.to_dict()}
                return plain(self._result, max_nodes=100000)
