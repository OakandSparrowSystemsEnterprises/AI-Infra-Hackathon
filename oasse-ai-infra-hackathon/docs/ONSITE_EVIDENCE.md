# Onsite Evidence Manifest

This file records evidence that was generated on the Intel event machine without committing large local artifacts, model weights, calibration state, camera captures, or receipt dumps.

## Governed learned-policy physical step

Artifact generated onsite:

```text
onsite/act-governed-first-physical-step.json
```

SHA-256:

```text
979cb3db04785c41f65069d56a240bfbd83ca1025c756f99a87f3567fac0e2df
```

Observed proof status:

```text
PHYSICALLY_VERIFIED
```

Authority result for the physical step:

```text
verdict = ALLOW
reasons = ['POLICY_SATISFIED']
EXACT_BINDING_OK
```

Encoder evidence from the same run:

```text
shoulder_pan.pos     before=  29.451 target=  20.450 after=  20.484
shoulder_lift.pos    before=  -2.593 target=   2.407 after=   2.418
elbow_flex.pos       before= -62.813 target= -58.237 after= -58.154
wrist_flex.pos       before=  94.725 target=  91.255 after=  92.176
wrist_roll.pos       before= -29.846 target= -27.206 after= -27.385
gripper.pos          before=  23.124 target=  22.820 after=  22.988
```

## Explicit deny path

Before the physical ACT step, the same authority path was exercised with the operator workspace interlock set false:

```text
verdict = DENY
reasons = ['WORKSPACE_OCCUPIED']
authorized_action = None
DENY_NO_HANDOFF_OK
```

No physical handoff occurred in that case.

## Closed-loop execution-path endurance

A later governed ACT rollout completed 600 individually evaluated `ALLOW / POLICY_SATISFIED` steps through the authority and SO-101 dispatch path. The rollout reached `MAX_STEPS_REACHED` and did **not** complete the LEGO manipulation task. This is evidence that the closed-loop authority/execution path ran for 600 steps, not evidence of task success.

The behavior analysis showed the first mixed-data ACT model converged to a narrow hold attractor with the gripper remaining near 23 degrees. Dataset inspection then identified idle and weak-manipulation episodes, leading to a clean retraining plan using episodes 5, 6, 8 and 9.

## Dataset summary used for retraining decision

The strongest observed action/gripper spans were:

```text
Episode 5: total motion 473.28, gripper span  6.19
Episode 6: total motion 398.59, gripper span 18.32
Episode 8: total motion 1114.54, gripper span 35.40
Episode 9: total motion 935.53, gripper span 36.81
```

Episodes 0-2 were effectively idle. Episodes 3-4 had little gripper signal. Episode 7 had substantial arm motion but only about 2.27 degrees of gripper span.

## Runtime identity

Recorded onsite runtime facts:

```text
LeRobot robot-control environment: 0.6.1
PyTorch: 2.14.0+xpu
Intel XPU device: Intel(R) Arc(TM) B390 GPU
OpenVINO development environment: 2026.3
```

## Evidence handling

Raw proofs, receipt dumps, frames, model checkpoints, datasets and calibration files remain generated/local artifacts. The repository `.gitignore` intentionally excludes those categories. This manifest is the small, reviewable pointer to the onsite results.

If a final autonomous LEGO pick-and-drop succeeds, add its proof artifact name, hash, receipt-chain hash and video reference here rather than committing the raw dataset or model checkpoint.
