"""Recheck a saved evidence directory without any robot, model or network."""
import argparse
import json
from pathlib import Path
from oasse_physical_ai.evidence_bundle import verify_bundle

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("--expected-manifest-sha256")
    args=parser.parse_args()
    print(json.dumps(verify_bundle(Path(args.directory),expected_manifest_sha256=args.expected_manifest_sha256),indent=2))
