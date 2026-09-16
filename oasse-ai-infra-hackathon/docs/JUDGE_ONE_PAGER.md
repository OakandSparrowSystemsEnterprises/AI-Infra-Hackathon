# Judge One-Pager

## **INTEL® PHYSICAL AI CHALLENGE**

### Gatekeeper: Pre-Execution Security for Physical AI

Built for **AI INFRA SUMMIT 2026** with **lablab.ai** and **Native**.

**Thesis:** Capability proposes. Authority decides. Execution follows authority, not capability.

## The problem

Physical AI can compress perception, planning and actuation into a machine-speed loop. Capability alone does not answer whether this exact actor, using this exact evidence, is authorized to cause this exact physical effect now.

## What we built

```text
camera / robot state
      -> trained ACT proposal
      -> bounded exact joint command
      -> pre-execution authority
      -> ALLOW | TRANSFORM | HOLD | DENY
      -> controlled SO-101 dispatch
      -> encoder-observed outcome
```

Optional Tenki-derived evidence can sit before authority, but it is explicitly `authority=false`. It may contribute evidence; it cannot authorize effect.

## Verified onsite physical proof

On the Intel event machine we verified:

1. **Intel XPU learned policy:** ACT trained and inferred on an Intel Arc B390 through PyTorch XPU.
2. **Real robot actuation:** the left 12 V SO-101 follower executed a trained-policy joint command with encoder readback.
3. **DENY means no handoff:** `workspace_clear=false` produced `DENY / WORKSPACE_OCCUPIED` and no physical dispatch.
4. **ALLOW is exact-bound:** `workspace_clear=true` produced `ALLOW / POLICY_SATISFIED`; the returned authorized action preserved the exact SHA-bound joint command.
5. **Physical outcome verification:** one ACT-generated action reached `PHYSICALLY_VERIFIED` with before/target/after encoder evidence.

A later governed rollout passed 600 individually authorized physical steps through the authority/execution path without that path collapsing. It reached `MAX_STEPS_REACHED`; it did **not** complete the LEGO task and is not represented as task success.

## The deeper architecture

Authority defines the admissible transition space:

$$
C_I:X_I\rightarrow X_I,
\qquad
I(C_I(x))=I(x)=\iota.
$$

The planner chooses proposals. Authority determines whether the proposed transition is executable. The invariant constrains action; it does not pretend to be the planner.

## Intel fit

The verified onsite stack includes:

- **Intel Arc B390 / PyTorch XPU** for ACT training and inference;
- **OpenVINO 2026.3** runtime bring-up;
- **LeRobot 0.6.1** ACT + SO-101 control;
- the Intel Physical AI Studio ecosystem as the event workflow context.

The MVTec PaDiM/OpenVINO artifact was runtime/integration bring-up evidence, **not** a LEGO detector. Robotics AI Suite is not claimed as independently verified in the final physical path.

## Why it matters

Monitoring after execution cannot prevent an unauthorized state transition. The authority boundary is placed immediately before physical effect. The system therefore distinguishes:

- what the model proposes;
- what the robot can physically do;
- what is authorized to execute;
- what actually happened afterward.

## Current task boundary

The original ten-episode imitation dataset contained significant idle data. Offline analysis isolated the strongest manipulation/gripper signal in episodes `5,6,8,9`. A clean ACT retrain uses only those episodes with shorter replanning intervals.

**Not yet claimed:** autonomous end-to-end LEGO pick-and-drop success.

## Reproducibility and evidence

The repository contains the parameterized ACT/SO-101 runners, dataset-analysis tooling, checkpoint inspection, native OpenVINO/MuJoCo rehearsal, deterministic authority tests, CI, and the onsite evidence manifest.

See:

- `docs/ONSITE_ACT_LEGO.md`
- `docs/ONSITE_EVIDENCE.md`
- `docs/ONSITE_REVIEW_CHECKLIST.md`

Raw datasets, model weights, camera frames, calibration files and credentials remain local/generated artifacts and are not committed.

## IP and claim boundary

The repository is greenfield MIT integration code. The onsite authority was the repository `ReferenceAuthorityEngine` behind the HTTP pre-execution boundary, not the separate proprietary production Gatekeeper runtime. Production Gatekeeper source and policy corpus are not distributed.
