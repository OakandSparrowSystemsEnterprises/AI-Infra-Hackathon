# Greenfield and MIT Provenance

This LabLab hackathon repository is a greenfield integration codebase. The current committed source tree was authored specifically for this project by Oak & Sparrow Systems Enterprise LLC and project contributors working in this repository.

## Repository license

All code, tests, scripts, documentation, configuration, reference implementations, demonstration fixtures, and other materials committed to this repository by the project are distributed under the MIT License in `LICENSE`.

The application copy of the license at `oasse-ai-infra-hackathon/LICENSE` is intentionally identical to the repository-root license.

## No copied tutorial implementation

No source code, model weights, assets, notebooks, or other implementation content from the previously reviewed external LeRobot/MuJoCo tutorial repository is vendored, copied, or adapted into the current submission tree. The simulation, adapters, authority shell, tests, documentation, and demo tooling in this repository are independently implemented for this hackathon.

External projects may be used as installed runtime dependencies or through documented public APIs. Their packages retain their own licenses and are not relicensed by this repository merely because the integration can call them.

## Proprietary boundary

The proprietary Gatekeeper production/runtime implementation, proprietary policy corpus, private infrastructure, credentials, trade secrets, and undistributed OASSE technology are not committed here. The MIT-licensed `GatekeeperClient`, reference authority engine, data contracts, integration logic, tests, and demo tooling are separate greenfield repository code.

## Commit policy

Do not commit third-party source trees, copied examples, model weights, datasets, robot assets, archives, or binary payloads unless the project has verified that the content may itself be distributed under the repository's MIT terms. Prefer package-manager dependencies, runtime downloads outside the repository, or locally generated artifacts excluded by `.gitignore`.

`oasse-ai-infra-hackathon/PROVENANCE.json` records the current policy, and `python scripts/check_greenfield.py` enforces the structural checks used by CI.
