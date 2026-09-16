# Submission Narrative and Demonstration State

## Description

Gatekeeper adds an independent pre-execution authority boundary to a physical-AI pipeline. Perception and robot state supply evidence, a trained policy proposes an action, and authority permits, transforms, holds or denies the proposed effect before dispatch. The integration binds evidence and action snapshots and records the observed result after an attempted physical effect.

The repository contains both a reproducible software rehearsal and a verified onsite hardware path. The software rehearsal uses native OpenVINO and MuJoCo with explicitly labeled reference components. The onsite path used a trained ACT policy, Intel XPU inference, a real SO-101 follower and encoder readback behind the repository reference authority boundary. Production Gatekeeper remains a separate proprietary service behind the API boundary and is not included in the MIT repository.

## Short pitch

A model can know what to do, and a robot can be capable of doing it, without having permission to do it now. We separate those questions. The learned policy proposes. The robot retains capability. Gatekeeper independently evaluates whether that exact action is authorized using that evidence at that time. If authority denies the transition, no physical handoff occurs. If authority permits it, the exact authorized command is bound to the evidence and can be compared with the observed physical result.

## Onsite evidence already verified

The Intel onsite session produced these concrete results:

- ACT training and inference on Intel Arc B390 through PyTorch XPU;
- real SO-101 state, actuation and encoder readback;
- `workspace_clear=false -> DENY / WORKSPACE_OCCUPIED -> no physical handoff`;
- `workspace_clear=true -> ALLOW / POLICY_SATISFIED` with exact joint-command/envelope preservation;
- one ACT-generated physical action with proof status `PHYSICALLY_VERIFIED`;
- a 600-step governed execution-path run without an authority/actuator-path collapse.

The 600-step run did not complete the LEGO task. It is execution-path evidence, not task-success evidence.

## Current learned-policy state

Offline dataset analysis showed that the original ten episodes contained substantial idle or weak-manipulation data. Episodes `5,6,8,9` carried the strongest gripper/manipulation signal. The clean-v2 ACT training plan therefore uses only those episodes and reduces `n_action_steps` to replan more frequently.

Full autonomous LEGO pick-and-drop remains pending until visible completion and its corresponding governed proof are recorded.

## Intel stack and claim discipline

Verified onsite:

- Intel Arc B390 / PyTorch XPU for ACT;
- LeRobot 0.6.1 for the ACT + SO-101 path;
- OpenVINO 2026.3 runtime bring-up.

The MVTec PaDiM artifact was used to verify the OpenVINO/Anomalib runtime path; it is not a LEGO detector. Physical AI Studio is part of the event workflow/ecosystem, while Robotics AI Suite is not claimed as independently verified in the final physical path.

## Demonstration framing

The strongest current live demonstration is the authority boundary itself:

1. show real robot state and learned-policy proposal;
2. show the exact bounded command and its execution-envelope hash;
3. show an occupied-workspace request receiving DENY with no dispatch;
4. show a clear-workspace request receiving ALLOW;
5. show encoder before/target/after values for the authority-approved physical movement;
6. show the evidence manifest and receipt/proof hash.

When the clean-v2 autonomous LEGO run succeeds, add that task-completion evidence without rewriting or weakening the authority semantics.

## Measurements and claims

Keep software-rehearsal and physical-hardware measurements separate. Report authority latency, inference latency and physical execution measurements only from their corresponding evidence. Do not use simulator wall-clock time as real robot cycle time. Preserve unknown, blocked, aborted and max-step outcomes instead of converting them into successes.

## Reproducibility

Use:

- `docs/ONSITE_ACT_LEGO.md` for the current event handoff;
- `docs/ONSITE_EVIDENCE.md` for physical proof hashes;
- `docs/ONSITE_REVIEW_CHECKLIST.md` before another physical run;
- `scripts/analyze_lerobot_dataset.py` for episode-signal inspection;
- `scripts/check_act_checkpoint.py` for checkpoint identity/configuration;
- `scripts/run_act_governed_single_step.py` and `scripts/run_act_governed_rollout.py` for the tracked physical runners.

Raw datasets, model weights, calibration files, frames, receipts and credentials remain local/generated artifacts and are intentionally excluded from Git.
