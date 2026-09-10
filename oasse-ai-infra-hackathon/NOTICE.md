# Source and IP Notice

Copyright (c) 2026 Oak & Sparrow Systems Enterprise LLC

## License for this repository

Everything actually distributed in this repository is licensed under the MIT License. The full license text is in the repository root [`LICENSE`](../LICENSE) file.

That grant covers the code and materials present here: the source under `src/`, the tests under `tests/`, the scripts, the Docker and packaging configuration, the documentation under `docs/`, and the demonstration materials. It includes the local reference authority engine in `src/oasse_physical_ai/policy.py` and the `GatekeeperClient` adapter in `src/oasse_physical_ai/gatekeeper_client.py`.

Nothing in this notice narrows, conditions, or withdraws the rights the MIT License grants to files that are present in this repository.

## What this repository does not contain or license

This repository is a hackathon integration and demonstration implementation. It does not contain, and the MIT License does not extend to, Oak & Sparrow Systems Enterprise LLC's separate proprietary technology, including:

- the Gatekeeper production/runtime source
- the proprietary policy corpus
- private enterprise integrations
- private infrastructure
- credentials, tokens, and secrets
- patents and patent applications
- trade secrets
- any other OASSE technology that is not distributed in this repository

Those items are not published here. No license to them is granted or implied by publication, demonstration, or submission of this repository. The MIT License applies to what is in the repository, not to what the repository references or connects to.

## Gatekeeper IP boundary

Gatekeeper is the authority boundary in the architecture this repository demonstrates:

```text
camera/sensor evidence
  -> perception
  -> VLA proposed action
  -> Gatekeeper authority evaluation
  -> ALLOW / TRANSFORM / HOLD / DENY
  -> controlled actuator
  -> sealed receipt
```

This repository consumes Gatekeeper through the `AuthorityClient` / `GatekeeperClient` API boundary defined in `src/oasse_physical_ai/gatekeeper_client.py`. `GatekeeperClient` is an MIT-licensed HTTP adapter. The service it calls when `AUTHORITY_MODE=live` is the proprietary Gatekeeper production implementation, which is not contained in this repository.

`ReferenceAuthorityEngine` in `src/oasse_physical_ai/policy.py` is a local, deterministic reference/simulation authority engine. It exists so the integration path is runnable without the production service, for local simulation, CI, judging rehearsals, and failure testing. It is MIT-licensed repository code. It is not the proprietary Gatekeeper production engine and must not be represented as such. Its small declared policy is not the proprietary policy corpus.

The evidence, action, decision, and receipt contracts that cross that boundary (`EvidenceFrame`, `ProposedAction`, `AuthorityDecision`, `Receipt` in `src/oasse_physical_ai/models.py`) are repository code and are MIT-licensed.
