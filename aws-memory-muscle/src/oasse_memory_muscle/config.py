from __future__ import annotations

from dataclasses import dataclass
import os


REQUIRED_RUNTIME_KEYS = (
    "ROCKETRIDE_API_KEY",
    "COGNEE_API_KEY",
    "HYDRADB_API_KEY",
    "HYDRADB_TENANT_ID",
    "HOTDATA_API_KEY",
    "ROTE_API_KEY",
    "SNYK_TOKEN",
    "GATEKEEPER_URL",
)

OPTIONAL_RUNTIME_KEYS = ("TENKI_API_KEY", "GATEKEEPER_API_KEY", "HOTDATA_WORKSPACE", "COGNEE_BASE_URL")


class BuildClosed(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    event_build_open: bool
    present_keys: frozenset[str]

    @classmethod
    def from_env(cls) -> "Settings":
        keys = frozenset(key for key in (*REQUIRED_RUNTIME_KEYS, *OPTIONAL_RUNTIME_KEYS) if os.getenv(key))
        return cls(event_build_open=os.getenv("EVENT_BUILD_OPEN", "0") == "1", present_keys=keys)

    @property
    def missing_required_keys(self) -> tuple[str, ...]:
        return tuple(key for key in REQUIRED_RUNTIME_KEYS if key not in self.present_keys)

    def require_build_open(self) -> None:
        if not self.event_build_open:
            raise BuildClosed("EVENT_BUILD_OPEN is closed; functional event wiring is intentionally disabled")
