from oasse_memory_muscle.contracts import ActionEnvelope, EvidenceRef, LearningEvent


def digest(char: str = "a") -> str:
    return char * 64


def test_action_digest_is_stable() -> None:
    evidence = EvidenceRef(source="snyk", ref="scan-1", sha256=digest("b"))
    a = ActionEnvelope("open_pr", "refs/heads/fix", "org/repo", "abc1234", digest("c"), "agent-1", (evidence,))
    b = ActionEnvelope("open_pr", "refs/heads/fix", "org/repo", "abc1234", digest("c"), "agent-1", (evidence,))
    assert a.digest == b.digest
    assert len(a.digest) == 64


def test_learning_event_digest_is_stable() -> None:
    evidence = EvidenceRef(source="tests", ref="pytest", sha256=digest("d"))
    event = LearningEvent("evt-1", "org/repo", "failure-x", "diagnosis", "fix", (evidence,), (), "decision-1", True)
    assert event.digest == event.digest
    assert len(event.digest) == 64
