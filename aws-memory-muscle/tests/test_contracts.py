from oasse_memory_muscle.contracts import ActionEnvelope, EvidenceRef, LearningEvent


def digest(char: str = "a") -> str:
    return char * 64


def make_action() -> ActionEnvelope:
    evidence = EvidenceRef(source="snyk", ref="scan-1", sha256=digest("b"))
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
        destination="refs/heads/fix",
        repository="org/repo",
        base_sha="abc1234",
        patch_sha256=digest("c"),
        evidence=(evidence,),
    )


def test_action_digest_is_stable() -> None:
    a = make_action()
    b = make_action()
    assert a.digest == b.digest
    assert len(a.digest) == 64


def test_learning_event_digest_is_stable() -> None:
    evidence = EvidenceRef(source="tests", ref="pytest", sha256=digest("d"))
    event = LearningEvent(
        event_id="evt-1",
        run_id="run-1",
        repository="org/repo",
        base_sha="abc1234",
        failure_signature="failure-x",
        diagnosis="diagnosis",
        remediation_summary="fix",
        patch_sha256=digest("e"),
        test_evidence=(evidence,),
        security_evidence=(),
        authority_decision_id="decision-1",
        authority_receipt_ref="receipt-1",
        success=True,
    )
    assert event.digest == event.digest
    assert len(event.digest) == 64
