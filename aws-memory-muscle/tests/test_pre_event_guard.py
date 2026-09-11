import pytest

from oasse_memory_muscle.config import BuildClosed, Settings
from oasse_memory_muscle.runtime import CompositionRoot


def test_build_is_closed_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EVENT_BUILD_OPEN", raising=False)
    settings = Settings.from_env()
    assert settings.event_build_open is False
    with pytest.raises(BuildClosed):
        CompositionRoot.wire(settings)


def test_open_build_still_has_no_pre_event_implementations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVENT_BUILD_OPEN", "1")
    settings = Settings.from_env()
    with pytest.raises(NotImplementedError):
        CompositionRoot.wire(settings)
