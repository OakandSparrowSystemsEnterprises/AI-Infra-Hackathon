# Gatekeeper: Pre-Execution Security for Physical AI

## **INTEL® PHYSICAL AI CHALLENGE**

Built for **AI INFRA SUMMIT 2026** with the **lablab.ai** and **Native** hackathon ecosystem.

> **Capability proposes. Authority decides. Execution follows authority, not capability.**

Oak & Sparrow Systems Enterprise LLC built a greenfield MIT-licensed integration that inserts an independent machine-speed authority boundary immediately before physical effect.

```text
camera + robot state
        -> perception / learned policy
        -> ProposedAction
        -> optional derived evidence (authority=false)
        -> pre-execution authority
        -> ALLOW | TRANSFORM | HOLD | DENY
        -> controlled physical execution
        -> observed outcome / receipts
```

The planner and robot retain capability. They do not grant themselves execution authority.

The deeper architecture treats authority as an admissible transition space:

```math
C_I:X_I\rightarrow X_I
\qquad\text{and}\qquad
I(C_I(x))=I(x)=\iota.
```

The invariant constrains what may execute; it does not pretend to be the planner.

## Current verified state

The September 15 Intel onsite session moved the project beyond software-only rehearsal.

Verified on the event hardware:

- **Intel Arc B390 / PyTorch XPU** ACT training and inference;
- **LeRobot 0.6.1** ACT + SO-101 control;
- real left 12 V SO-101 follower actuation with encoder readback;
- explicit `DENY / WORKSPACE_OCCUPIED` with **no physical handoff**;
- explicit `ALLOW / POLICY_SATISFIED` with exact SHA-bound joint-command preservation;
- one ACT-generated physical action with proof status **`PHYSICALLY_VERIFIED`**;
- a 600-step governed authority/execution-path run without path collapse.

The 600-step run reached `MAX_STEPS_REACHED` and did **not** complete the LEGO task. It is execution-path evidence, not task-success evidence.

The first ten imitation episodes mixed idle and manipulation data. Offline analysis isolated episodes `5,6,8,9` as the strongest manipulation/gripper set. Clean-v2 ACT retraining uses those episodes with shorter replanning intervals.

**Pending:** full autonomous LEGO pick-and-drop proof.

## Intel / Physical AI stack claim boundary

Verified onsite:

- Intel Arc B390 XPU for ACT;
- OpenVINO 2026.3 runtime/integration bring-up;
- LeRobot 0.6.1 SO-101 path.

Physical AI Studio is part of the event workflow/ecosystem. The **Anomalib / MVTec PaDiM / OpenVINO** artifact was runtime/integration bring-up evidence, **not** a LEGO detector. Robotics AI Suite is not claimed as independently verified in the final physical path.

The repository's verified onsite authority was `ReferenceAuthorityEngine` behind the HTTP pre-execution boundary. It is **not** represented as the separate proprietary production Gatekeeper runtime.

## Read this first

- [Onsite ACT + SO-101 handoff](oasse-ai-infra-hackathon/docs/ONSITE_ACT_LEGO.md)
- [Onsite evidence manifest](oasse-ai-infra-hackathon/docs/ONSITE_EVIDENCE.md)
- [Onsite review checklist](oasse-ai-infra-hackathon/docs/ONSITE_REVIEW_CHECKLIST.md)
- [Judge one-pager](oasse-ai-infra-hackathon/docs/JUDGE_ONE_PAGER.md)
- [Final demo script](oasse-ai-infra-hackathon/docs/DEMO_SCRIPT_FINAL.md)
- [Final project draft](oasse-ai-infra-hackathon/docs/FINAL_DRAFT.md)
- [Senior engineer architecture review](oasse-ai-infra-hackathon/docs/SENIOR_ENGINEER_ARCHITECTURE.md)
- [Authority invariant architecture](oasse-ai-infra-hackathon/docs/AUTHORITY_INVARIANT.md)
- [Application README](oasse-ai-infra-hackathon/README.md)

Historical/pre-onsite planning documents are retained only for provenance and should not override the current onsite handoff.

## Reusable physical runners

From `oasse-ai-infra-hackathon`:

```text
scripts/analyze_lerobot_dataset.py
scripts/check_act_checkpoint.py
scripts/run_act_governed_single_step.py
scripts/run_act_governed_rollout.py
```

The physical runners require explicit robot identity and execution interlocks. The rollout can derive state/action guard ranges from the same episode subset used for training, e.g. `--dataset-episodes 5,6,8,9`.

`MAX_STEPS_REACHED` and `OPERATOR_ABORT` are incomplete runs, not successful task exits.

## Software rehearsal

The repository also contains a reproducible native OpenVINO + MuJoCo rehearsal covering deterministic authority scenarios including ALLOW, TRANSFORM, HOLD, DENY, stale/replayed evidence, authority outage and receipt verification.

Simulation, physical hardware and production-service claims remain separately labeled.

## Tenki boundary

Tenki is optional isolated pre-authority compute. A valid claim must remain `authority=false` and bind to the exact artifact/effect/principal. Tenki does not return an executable verdict or authorized action.

The adapter/contract is tested, but a current live Tenki worker is not claimed unless a fresh event probe supports it.

## Greenfield MIT / IP boundary

Everything authored and committed in this repository is greenfield MIT project code. External runtimes remain separately licensed dependencies and are not vendored or relicensed here.

Proprietary Gatekeeper production source, policy corpus, credentials and private infrastructure remain outside this repository behind the integration/API boundary.

See [GREENFIELD.md](GREENFIELD.md), [PROVENANCE.json](oasse-ai-infra-hackathon/PROVENANCE.json), [LICENSE](LICENSE) and [NOTICE](oasse-ai-infra-hackathon/NOTICE.md).
