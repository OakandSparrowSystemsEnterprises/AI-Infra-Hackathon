from __future__ import annotations

from oasse_memory_muscle.config import OPTIONAL_RUNTIME_KEYS, REQUIRED_RUNTIME_KEYS, Settings


def main() -> None:
    settings = Settings.from_env()
    print("OASSE AWS Memory to Muscle Memory skeleton")
    print(f"event_build_open={settings.event_build_open}")
    for key in REQUIRED_RUNTIME_KEYS:
        print(f"required {key}: {'present' if key in settings.present_keys else 'missing'}")
    for key in OPTIONAL_RUNTIME_KEYS:
        print(f"optional {key}: {'present' if key in settings.present_keys else 'missing'}")
    if settings.missing_required_keys:
        print("runtime readiness: incomplete")
    else:
        print("runtime readiness: credentials present; connectivity still requires event-time verification")


if __name__ == "__main__":
    main()
