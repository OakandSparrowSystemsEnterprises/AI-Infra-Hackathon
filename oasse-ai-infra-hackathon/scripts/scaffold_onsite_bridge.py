"""Create ignored onsite sponsor bridge files without overwriting existing work."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="onsite")
    args = parser.parse_args()

    app = Path(__file__).resolve().parents[1]
    output = Path(args.output_dir)
    if not output.is_absolute():
        output = app / output
    output.mkdir(parents=True, exist_ok=True)

    sources = {
        app / "examples" / "onsite_bridge.py": output / "onsite_bridge.py",
        app / "config" / "sponsor-bindings.example.json": output / "bindings.json",
    }
    existing = [str(target) for target in sources.values() if target.exists()]
    if existing:
        raise SystemExit("refusing to overwrite existing onsite files: " + ", ".join(existing))

    for source, target in sources.items():
        shutil.copyfile(source, target)

    print(f"created {output / 'onsite_bridge.py'}")
    print(f"created {output / 'bindings.json'}")
    print("edit only the thin sponsor callbacks, then run validate_sponsor_bindings.py")


if __name__ == "__main__":
    main()
