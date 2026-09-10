from dataclasses import dataclass
import os


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    return default if raw is None else raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    authority_mode: str = os.getenv("AUTHORITY_MODE", "reference")
    gatekeeper_url: str = os.getenv("GATEKEEPER_URL", "")
    gatekeeper_token: str = os.getenv("GATEKEEPER_TOKEN", "")
    evidence_max_age_ms: int = int(os.getenv("EVIDENCE_MAX_AGE_MS", "500"))
    min_confidence: float = float(os.getenv("MIN_CONFIDENCE", "0.80"))
    max_speed_mps: float = float(os.getenv("MAX_SPEED_MPS", "0.35"))
    workspace_clear_required: bool = _bool("WORKSPACE_CLEAR_REQUIRED", True)


settings = Settings()
