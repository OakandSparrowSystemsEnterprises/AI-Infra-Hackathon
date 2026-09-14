"""Fail CI if the submission tree stops matching the greenfield MIT policy."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent

FORBIDDEN_DIR_NAMES = {"vendor", "vendors", "third_party", "third-party", "externals", "submodules"}
FORBIDDEN_PAYLOAD_SUFFIXES = {
    ".onnx", ".pt", ".pth", ".ckpt", ".safetensors", ".tflite", ".engine", ".gguf",
    ".zip", ".7z", ".rar", ".tar", ".tgz", ".whl", ".jar", ".dll", ".dylib", ".a", ".lib",
}


def tracked_entries() -> list[tuple[str, str]]:
    out = subprocess.check_output(["git", "ls-files", "-s"], cwd=ROOT, text=True)
    entries = []
    for line in out.splitlines():
        mode, _sha, _stage_path = line.split(maxsplit=2)
        path = line.split("\t", 1)[1] if "\t" in line else _stage_path.split(maxsplit=1)[-1]
        entries.append((mode, path))
    return entries


def main() -> None:
    errors: list[str] = []

    root_license = (ROOT / "LICENSE").read_bytes()
    app_license = (APP / "LICENSE").read_bytes()
    if root_license != app_license:
        errors.append("root and application LICENSE files differ")
    if not root_license.startswith(b"MIT License\n"):
        errors.append("LICENSE is not the MIT License")

    pyproject = (APP / "pyproject.toml").read_text(encoding="utf-8")
    if 'license = "MIT"' not in pyproject:
        errors.append("pyproject.toml does not declare MIT")

    provenance = json.loads((APP / "PROVENANCE.json").read_text(encoding="utf-8"))
    if provenance.get("repository_license") != "MIT" or provenance.get("greenfield") is not True:
        errors.append("PROVENANCE.json does not declare greenfield MIT")
    for key in ("third_party_committed_source", "third_party_committed_model_weights", "third_party_committed_assets"):
        if provenance.get(key) != []:
            errors.append(f"{key} is not empty; review licensing before merge")
    if provenance.get("proprietary_gatekeeper_source_committed") is not False:
        errors.append("proprietary Gatekeeper source provenance is not false")

    entries = tracked_entries()
    if any(mode == "160000" for mode, _ in entries):
        errors.append("git submodule/gitlink found in submission tree")
    if (ROOT / ".gitmodules").exists():
        errors.append(".gitmodules is present")

    for _mode, raw in entries:
        path = Path(raw)
        lowered_parts = {part.lower() for part in path.parts}
        if lowered_parts & FORBIDDEN_DIR_NAMES:
            errors.append(f"vendored/third-party directory is tracked: {raw}")
        lower_name = path.name.lower()
        if any(lower_name.endswith(suffix) for suffix in FORBIDDEN_PAYLOAD_SUFFIXES):
            errors.append(f"binary/model/archive payload requires explicit provenance review: {raw}")

    required = [ROOT / "GREENFIELD.md", APP / "NOTICE.md", APP / "PROVENANCE.json"]
    for path in required:
        if not path.is_file():
            errors.append(f"required provenance file missing: {path.relative_to(ROOT)}")

    if errors:
        print("Greenfield/MIT policy check FAILED:", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        raise SystemExit(1)

    print(f"Greenfield/MIT policy check passed for {len(entries)} tracked files")


if __name__ == "__main__":
    main()
