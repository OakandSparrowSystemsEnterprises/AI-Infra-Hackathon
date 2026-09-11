from __future__ import annotations

from dataclasses import dataclass

from .contracts import ActionEnvelope, AuthorityDecision, Verdict


class AuthorizationRequired(RuntimeError):
    """Raised when no exact executable authorization exists."""


@dataclass(frozen=True)
class AuthorizedEffect:
    action: ActionEnvelope
    decision_id: str
    receipt_ref: str | None


def authorize_effect(action: ActionEnvelope, decision: AuthorityDecision) -> AuthorizedEffect:
    """Convert a Gatekeeper decision into an executable effect or fail closed.

    This function is intentionally sponsor-agnostic. It is a contract guard, not a
    hackathon-specific authority integration.
    """
    if decision.action_sha256 != action.digest:
        raise AuthorizationRequired("authority decision is not bound to the exact proposed action")

    if decision.verdict in (Verdict.HOLD, Verdict.DENY):
        raise AuthorizationRequired(f"effect blocked by verdict {decision.verdict.value}")

    if decision.verdict is Verdict.ALLOW:
        executable = action
    elif decision.verdict is Verdict.TRANSFORM:
        assert decision.transformed_action is not None
        executable = decision.transformed_action
    else:
        raise AuthorizationRequired("unknown authority verdict")

    return AuthorizedEffect(action=executable, decision_id=decision.decision_id, receipt_ref=decision.receipt_ref)
