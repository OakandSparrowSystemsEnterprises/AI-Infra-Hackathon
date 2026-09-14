# Gatekeeper: Pre-Execution Security for Physical AI

Oak & Sparrow Systems Enterprise LLC's AI Infra Hackathon integration demonstrates independent authority between proposed action and physical effect. The runnable application remains in `oasse-ai-infra-hackathon/`. No directories have been relocated.

## Start here

The version 0.4 software rehearsal uses native OpenVINO inference over rendered RGB and native MuJoCo dynamics to inspect, transport and release a cube, then separately verify its destination. The detector and planner are reference implementations, and the grip is an idealized Cartesian suction constraint. This is not yet an SO-101 hardware or trained-model result.

Read the [application README](oasse-ai-infra-hackathon/README.md) for the reference API console. Use the [Phase 4 guide](oasse-ai-infra-hackathon/docs/PHASE4_INSPECTION.md) for the complete native rehearsal and offline evidence package. The [onsite runbook](oasse-ai-infra-hackathon/docs/ON_SITE_RUNBOOK.md) defines the real camera, Anomalib, VLA and controller handoff. The [live Gatekeeper probe](oasse-ai-infra-hackathon/docs/GATEKEEPER_LIVE_ACCEPTANCE.md) checks the deployed response contract without moving a robot. The [submission narrative](oasse-ai-infra-hackathon/docs/SUBMISSION_NARRATIVE.md) supplies the pitch and recorded-demo structure.

From the app directory, `python scripts/rehearse_submission.py --profile native --output /tmp/oasse-rehearsal` runs the test and demo evidence sequence after the optional native dependencies and rendering backend are installed. It never auto-installs drivers or commands hardware. Open the resulting `inspection/index.html` for the recorded demonstration. Verify its manifest and receipts with `scripts/verify_evidence.py`.

## Licensing and IP boundary

The MIT License applies to code and materials actually distributed here, including the local reference engine and API adapters. The separate proprietary Gatekeeper production implementation, policy corpus, private infrastructure, secrets and undistributed technology are not included. Nothing in the notice narrows MIT rights over repository files. See [LICENSE](LICENSE) and [NOTICE](oasse-ai-infra-hackathon/NOTICE.md).

Passing the software rehearsal does not mark onsite hardware acceptance or online submission complete. `submission.json` and the generated readiness report keep those states separate.
