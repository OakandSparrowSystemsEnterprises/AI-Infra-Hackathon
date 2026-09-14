# Gatekeeper: Pre-Execution Security for Physical AI

Oak & Sparrow Systems Enterprise LLC's AI Infra Hackathon integration demonstrates independent authority between proposed action and physical effect. The runnable application remains in `oasse-ai-infra-hackathon/`.

## Start here

The software rehearsal uses native OpenVINO inference over rendered RGB and native MuJoCo dynamics to inspect, transport and release a cube, then separately verify its destination. The detector and planner are reference implementations, and the grip is an idealized Cartesian suction constraint. This is not yet an SO-101 hardware or trained-model result.

Read the [application README](oasse-ai-infra-hackathon/README.md), [onsite runbook](oasse-ai-infra-hackathon/docs/ON_SITE_RUNBOOK.md), [live Gatekeeper acceptance guide](oasse-ai-infra-hackathon/docs/GATEKEEPER_LIVE_ACCEPTANCE.md), and [submission narrative](oasse-ai-infra-hackathon/docs/SUBMISSION_NARRATIVE.md).

## Greenfield MIT repository

This LabLab submission tree is greenfield project code. Everything project-authored and committed here is distributed under the MIT License. No external tutorial source, model weights, assets, notebooks, or copied implementation are included in the current submission tree. External runtimes are dependencies and retain their own licenses; they are not being relicensed as repository content.

The proprietary Gatekeeper production/runtime implementation and proprietary policy corpus are not committed. The MIT-licensed API adapter, reference engine, data contracts, integration code, tests, simulation harness, documentation, and submission tooling are separate repository implementations.

See [GREENFIELD.md](GREENFIELD.md), [LICENSE](LICENSE), [NOTICE](oasse-ai-infra-hackathon/NOTICE.md), and [PROVENANCE.json](oasse-ai-infra-hackathon/PROVENANCE.json). CI runs the greenfield policy checker on every change.

Passing the software rehearsal does not mark onsite hardware acceptance or online submission complete. `submission.json` and the generated readiness report keep those states separate.
