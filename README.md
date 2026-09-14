# Gatekeeper: Pre-Execution Security for Physical AI

## **INTEL® PHYSICAL AI CHALLENGE**

### **INTEL® CORE™ ULTRA · OPENVINO™ · ANOMALIB · PHYSICAL AI STUDIO · ROBOTICS AI SUITE**

Built for **AI INFRA SUMMIT 2026** with the **lablab.ai** and **Native** hackathon ecosystem.

> **Capability proposes. Authority decides. Execution follows authority, not capability.**

Oak & Sparrow Systems Enterprise LLC built a greenfield MIT-licensed authority layer for Physical AI. **INTEL** supplies the capability surface that makes the challenge interesting: edge compute, accelerated inference and robotics tooling. Gatekeeper adds the independent machine-speed authority boundary immediately before physical effect.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                         INTEL PHYSICAL AI STACK                              │
│  Core Ultra -> OpenVINO -> Anomalib -> Physical AI / VLA -> Robotics       │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ EvidenceFrame + ProposedAction
                                       v
                         ┌───────────────────────────┐
                         │ GATEKEEPER AUTHORITY      │
                         │ exact actor + evidence    │
                         │ exact action + time       │
                         │ ALLOW / TRANSFORM         │
                         │ HOLD / DENY               │
                         └─────────────┬─────────────┘
                                       │ AuthorizedAction only
                                       v
┌──────────────────────────────────────┴───────────────────────────────────────┐
│                    CONTROLLED PHYSICAL EXECUTION                            │
│          robot command -> observed outcome -> chained receipts              │
└──────────────────────────────────────────────────────────────────────────────┘
```

The deeper architecture treats authority as an **admissible transition space**, not merely a rule checked after planning:

```text
Observe -> Propose -> Project into the admissible state space -> Execute -> Prove
```

with the compact invariant

```math
C_I:X_I\rightarrow X_I
\qquad\text{and}\qquad
I(C_I(x))=I(x)=\iota.
```

## Read this first

- [Senior engineer architecture review](oasse-ai-infra-hackathon/docs/SENIOR_ENGINEER_ARCHITECTURE.md)
- [Final project draft](oasse-ai-infra-hackathon/docs/FINAL_DRAFT.md)
- [Authority invariant architecture](oasse-ai-infra-hackathon/docs/AUTHORITY_INVARIANT.md)
- [Sponsor showcase strategy](oasse-ai-infra-hackathon/docs/SPONSOR_SHOWCASE.md)
- [Judge one-pager](oasse-ai-infra-hackathon/docs/JUDGE_ONE_PAGER.md)
- [Final demo script](oasse-ai-infra-hackathon/docs/DEMO_SCRIPT_FINAL.md)
- [Tomorrow onsite runbook](oasse-ai-infra-hackathon/docs/TOMORROW_ONSITE.md)
- [Application README](oasse-ai-infra-hackathon/README.md)

## **Sponsor-visible proof**

**INTEL** is the challenge sponsor, so Intel technology is visible in the proof rather than buried in setup. The software rehearsal already verifies native compiled **OPENVINO** inference. Onsite, the demo is designed to show the actual OpenVINO runtime/device, **ANOMALIB** anomaly evidence when the trained workflow is verified, and the real role of **PHYSICAL AI STUDIO** and **ROBOTICS AI SUITE** when those event components are bound.

Run `python scripts/sponsor_showcase.py --output onsite/sponsor-runtime.json` from the application directory to generate a non-actuating sponsor-runtime record. It records runtime facts without converting package presence into an unearned hardware or trained-model claim.

**AI INFRA SUMMIT**, **lablab.ai** and **Native** are credited prominently as the event/hackathon ecosystem. Event-level Diamond Partners are recognized in the sponsor document without implying that every event sponsor is part of this project's technical dependency graph.

## Current proof

The reproducible software rehearsal demonstrates native OpenVINO inference, native MuJoCo dynamics, normal/defective routing, transformed motion, stale/replayed evidence holds, authority-outage fail-closed behavior, post-action verification and chained receipts.

A detected defect does not automatically equal an authority violation. **Perception supplies facts; authority determines admissibility.** Likewise, the authority invariant constrains what may execute but does not claim to choose the uniquely optimal action.

The software rehearsal intentionally labels its detector, planner and grip as reference components. Onsite hardware, trained Anomalib/VLA use and production Gatekeeper are upgraded from *pending* only after evidence from the actual run exists.

## Greenfield MIT boundary

Everything authored and committed in this LabLab repository is greenfield MIT project code. External runtimes remain separately licensed dependencies and are not vendored or relicensed here. Proprietary Gatekeeper production source remains outside the repository behind the MIT-licensed adapter boundary.

See [GREENFIELD.md](GREENFIELD.md), [PROVENANCE.json](oasse-ai-infra-hackathon/PROVENANCE.json), [LICENSE](LICENSE) and [NOTICE](oasse-ai-infra-hackathon/NOTICE.md).
