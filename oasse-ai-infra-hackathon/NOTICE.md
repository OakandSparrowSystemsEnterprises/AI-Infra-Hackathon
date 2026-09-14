# Source and IP Notice

Copyright (c) 2026 Oak & Sparrow Systems Enterprise LLC

## License for this repository

Everything actually distributed in this repository is licensed under the MIT License. The full license text is in [`LICENSE`](LICENSE) in this directory and in the repository root [`LICENSE`](../LICENSE). The two files are identical.

That grant covers the code and materials present here: source, tests, scripts, Docker and packaging configuration, documentation, reference implementations, and demonstration materials. Nothing in this notice narrows, conditions, or withdraws the rights the MIT License grants to files present in this repository.

## Greenfield provenance

The current submission tree is a greenfield hackathon implementation. No source code, model weights, assets, notebooks, or other implementation content from the previously reviewed external LeRobot/MuJoCo tutorial repository is vendored, copied, or adapted into the current submission tree. The project code in this repository is independently implemented for this hackathon.

External software such as OpenVINO, MuJoCo, LeRobot, Anomalib, OpenCV, NumPy, FastAPI, and related tools may be installed or called as runtime dependencies. Those packages retain their own licenses and are not relicensed by this repository. Their presence in an environment does not change the MIT license on project-authored repository content.

See the repository-root [`GREENFIELD.md`](../GREENFIELD.md) and [`PROVENANCE.json`](PROVENANCE.json). CI runs `scripts/check_greenfield.py` to guard this boundary structurally.

## What this repository does not contain or license

This repository does not contain Oak & Sparrow Systems Enterprise LLC's separate proprietary technology, including:

- the Gatekeeper production/runtime source
- the proprietary policy corpus
- private enterprise integrations
- private infrastructure
- credentials, tokens, and secrets
- patents and patent applications
- trade secrets
- other OASSE technology not distributed in this repository

Those items are not published here. No license to them is granted or implied by publication, demonstration, or submission of this repository. The MIT License applies to what is actually committed here, not to external services the integration references or calls.

## Gatekeeper IP boundary

Gatekeeper is the authority boundary in the demonstrated architecture:

```text
camera/sensor evidence
  -> perception
  -> VLA proposed action
  -> Gatekeeper authority evaluation
  -> ALLOW / TRANSFORM / HOLD / DENY
  -> controlled actuator
  -> sealed decision receipt (chained outcome receipt on execution)
```

This repository consumes Gatekeeper through the `AuthorityClient` / `GatekeeperClient` API boundary. `GatekeeperClient` is MIT-licensed repository code. The external production service it may call in live mode is proprietary and is not contained here.

`ReferenceAuthorityEngine` is a local deterministic reference/simulation authority engine for CI, rehearsals, and failure testing. It is MIT-licensed repository code and is not represented as the proprietary production engine or proprietary policy corpus.

The repository data contracts, adapters, orchestration, receipts, tests, simulation harnesses, camera interfaces, documentation, and submission tooling are MIT-licensed project code.
