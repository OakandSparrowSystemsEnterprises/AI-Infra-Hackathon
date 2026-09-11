import pytest

from oasse_memory_muscle.boundary import AuthorizationRequired, authorize_effect
from oasse_memory_muscle.contracts import ActionEnvelope, AuthorityDecision, Verdict


def digest(char: str = "a") -> str:
    return char * 64


def action(destination: str = "refs/heads/fix") -> ActionEnvelope:
    return ActionEnvelope(
        tenant_id="oasse-demo",
        principal_id="rocketride-agent-1",
        actor_type="agent",
        session_id="session-1",
        delegation_id=None,
        source="rocketride",
        adapter="aws-memory-muscle",
        transaction_id="txn-1",
        parent_action_id=None,
        domain="software.change",
        action_type="open_pr",
        requested_effect="create_pull_request",
        resource="org/repo",
        destination=destination,
        repository="org/repo",
        base_sha="abc1234",
        patch_sha256=digest("b"),
    )


def test_allow_executes_only_exact_bound_action() -> None:
    proposed = action()
    decision = AuthorityDecision("d-1", Verdict.ALLOW, proposed.digest, receipt_ref="receipt-1")
    authorized = authorize_effect(proposed, decision)
    assert authorized.action == proposed


def test_hold_and_deny_fail_closed() -> None:
    proposed = action()
    for verdict in (Verdict.HOLD, Verdict.DENY):
        with pytest.raises(AuthorizationRequired):
            authorize_effect(proposed, AuthorityDecision("d", verdict, proposed.digest))


def test_digest_mismatch_fails_closed() -> None:
    proposed = action()
    with pytest.raises(AuthorizationRequired):
        authorize_effect(proposed, AuthorityDecision("d", Verdict.ALLOW, digest("f")))


def test_transform_executes_only_transformed_action() -> None:
    proposed = action()
    transformed = action("refs/heads/safe-fix")
    decision = AuthorityDecision("d", Verdict.TRANSFORM, proposed.digest, transformed_action=transformed)
    authorized = authorize_effect(proposed, decision)
    assert authorized.action == transformed
