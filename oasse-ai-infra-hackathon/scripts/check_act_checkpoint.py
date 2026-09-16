from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Load and inspect a local LeRobot ACT checkpoint without robot I/O.")
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--hash-weights", action="store_true")
    args = parser.parse_args()

    from lerobot.policies.act import ACTPolicy

    policy = ACTPolicy.from_pretrained(args.checkpoint)
    config_path = args.checkpoint / "config.json"
    weights_path = args.checkpoint / "model.safetensors"

    result = {
        "checkpoint": str(args.checkpoint.resolve()),
        "type": type(policy).__name__,
        "chunk_size": policy.config.chunk_size,
        "n_action_steps": policy.config.n_action_steps,
        "temporal_ensemble_coeff": policy.config.temporal_ensemble_coeff,
        "configured_device": policy.config.device,
        "config_present": config_path.is_file(),
        "weights_present": weights_path.is_file(),
    }
    if config_path.is_file():
        result["config_sha256"] = sha256(config_path)
    if args.hash_weights and weights_path.is_file():
        result["weights_sha256"] = sha256(weights_path)

    print(json.dumps(result, indent=2))
    return 0 if result["config_present"] and result["weights_present"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
