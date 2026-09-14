# Gatekeeper: Pre-Execution Security for Physical AI

**Intel Physical AI Challenge | AI Infra Summit Hackathon**

> **Capability proposes. Authority decides. Execution follows authority, not capability.**

Oak & Sparrow Systems Enterprise LLC built a greenfield MIT-licensed authority layer for physical AI. Intel's Physical AI stack supplies the capability to perceive and act at machine speed. Gatekeeper adds an independent deterministic decision immediately before physical effect.

```text
camera / sensor
  -> Intel / OpenVINO perception
  -> EvidenceFrame
  -> VLA / planner proposal
  -> Gatekeeper authority
  -> ALLOW | TRANSFORM | HOLD | DENY
  -> controlled actuator
  -> post-action verification
  -> chained receipts
```

## Start with the final draft

- [Final project draft](oasse-ai-infra-hackathon/docs/FINAL_DRAFT.md)
- [Sponsor showcase strategy](oasse-ai-infra-hackathon/docs/SPONSOR_SHOWCASE.md)
- [Judge one-pager](oasse-ai-infra-hackathon/docs/JUDGE_ONE_PAGER.md)
- [Final demo script](oasse-ai-infra-hackathon/docs/DEMO_SCRIPT_FINAL.md)
- [Tomorrow onsite runbook](oasse-ai-infra-hackathon/docs/TOMORROW_ONSITE.md)
- [Application README](oasse-ai-infra-hackathon/README.md)

## Sponsor-visible proof

Intel is the challenge sponsor, so Intel technology is made visible in the proof rather than buried in setup. The software rehearsal already verifies native compiled OpenVINO inference. Onsite, the demo is designed to show the actual OpenVINO runtime/device, the Anomalib anomaly evidence when the trained workflow is verified, and the role of Physical AI Studio / Robotics AI Suite when those event components are bound.

Run `python scripts/sponsor_showcase.py --output onsite/sponsor-runtime.json` from the application directory to generate a non-actuating sponsor runtime record. It does not claim hardware or trained-model use merely because software is installed.

AI Infra Summit, lablab.ai and Native are credited as the event/hackathon ecosystem separately from the technical sponsor proof.

## Current proof

The reproducible software rehearsal currently demonstrates native OpenVINO inference, native MuJoCo dynamics, normal/defective routing, transformed motion, stale/replayed evidence holds, authority-outage fail-closed behavior, post-action verification and chained receipts.

The software rehearsal intentionally labels its detector, planner and grip as reference components. Onsite hardware, trained Anomalib/VLA use and production Gatekeeper are upgraded from *pending* only after evidence from the actual run exists.

## Greenfield MIT boundary

Everything authored and committed in this LabLab repository is greenfield MIT project code. External runtimes remain separately licensed dependencies and are not vendored or relicensed here. Proprietary Gatekeeper production source remains outside the repository behind the MIT-licensed adapter boundary.

See [GREENFIELD.md](GREENFIELD.md), [PROVENANCE.json](oasse-ai-infra-hackathon/PROVENANCE.json), [LICENSE](LICENSE) and [NOTICE](oasse-ai-infra-hackathon/NOTICE.md).
