# Gatekeeper: Pre-Execution Security for Physical AI

Oak & Sparrow Systems Enterprise LLC's AI Infra Hackathon integration demonstrates independent authority between proposed action and physical effect. The runnable application is in `oasse-ai-infra-hackathon/`.

## Final draft

The canonical judge-facing draft is [`docs/FINAL_DRAFT.md`](oasse-ai-infra-hackathon/docs/FINAL_DRAFT.md). For a one-minute review, use [`docs/JUDGE_ONE_PAGER.md`](oasse-ai-infra-hackathon/docs/JUDGE_ONE_PAGER.md). The exact presentation sequence is in [`docs/DEMO_SCRIPT_FINAL.md`](oasse-ai-infra-hackathon/docs/DEMO_SCRIPT_FINAL.md).

The project thesis is simple: **Capability proposes. Authority decides. Execution follows authority, not capability.**

## Current state

The software rehearsal uses native OpenVINO inference over rendered RGB and native MuJoCo dynamics to inspect, transport and release a cube, then separately verify its destination. The detector and planner are reference implementations, and the software grip is an idealized Cartesian suction constraint. Hardware-specific, trained-model and production-service claims stay false until onsite evidence proves them.

Use the [application README](oasse-ai-infra-hackathon/README.md) for runnable paths. Use the [tomorrow onsite runbook](oasse-ai-infra-hackathon/docs/TOMORROW_ONSITE.md) for hardware binding order. Use the [live Gatekeeper acceptance guide](oasse-ai-infra-hackathon/docs/GATEKEEPER_LIVE_ACCEPTANCE.md) for the non-actuating production contract probe.

From the app directory, `python scripts/rehearse_submission.py --profile native --output /tmp/oasse-rehearsal` runs the native evidence sequence after optional dependencies and a rendering backend are installed. `python scripts/check_submission_draft.py` validates the final-draft submission manifest. `python scripts/check_submission_draft.py --strict` is reserved for the final frozen submission after repository URL, video URL, final commit and submitted state have been filled.

## Greenfield MIT boundary

Everything authored and committed for this LabLab repository is intended to be distributable under MIT. External runtimes remain separately licensed dependencies and are not vendored or relicensed here. No source, assets, notebooks or model weights from the external LeRobot/MuJoCo tutorial are included; it was used as a workflow reference only.

Proprietary Gatekeeper production/runtime source, proprietary policy corpus, credentials, private infrastructure and other undistributed OASSE technology are not committed. The live service is consumed through the repository's MIT-licensed adapter.

See [LICENSE](LICENSE), [GREENFIELD.md](GREENFIELD.md), [`PROVENANCE.json`](oasse-ai-infra-hackathon/PROVENANCE.json), and [NOTICE](oasse-ai-infra-hackathon/NOTICE.md).

## Submission truth rule

The final claim set is the one supported by the frozen evidence. Simulation, onsite operator attestation and production-service verification remain separate. Passing software CI does not automatically make hardware, trained-model or production Gatekeeper claims true.
