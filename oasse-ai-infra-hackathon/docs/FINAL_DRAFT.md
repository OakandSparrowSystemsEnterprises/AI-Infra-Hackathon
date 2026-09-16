# Final Draft: Gatekeeper for Physical AI

## Project title

**Gatekeeper: Pre-Execution Security for Physical AI**

## Team

Oak & Sparrow Systems Enterprise LLC

## Challenge

Intel Physical AI Challenge

## One-line thesis

**Capability proposes. Authority decides. Execution follows authority, not capability.**

## Current status

The project has moved beyond software-only rehearsal. The September 15 onsite session verified a trained ACT policy on Intel XPU, real SO-101 actuation, an explicit DENY/no-handoff case, an ALLOW with exact command binding, and encoder-observed physical convergence for one learned-policy action.

Full autonomous LEGO pick-and-drop is **not yet claimed**. The first ten-episode imitation dataset contained substantial idle/weak data; clean-v2 retraining uses episodes `5,6,8,9` with shorter replanning intervals.

## Problem

Physical-AI systems are becoming fast enough to perceive, plan and act with very little human friction. That speed creates a missing control boundary. A model may be capable of generating a movement, and a robot may be technically capable of executing it, without that movement being authorized for the current actor, evidence, environment, timing or policy state.

This project places an independent deterministic authority decision immediately before physical effect. The execution path therefore distinguishes *what the system can do* from *what it is permitted to do now*.

## Solution

```text
camera / robot state
  -> evidence
  -> trained ACT / planner proposal
  -> bounded ProposedAction
  -> pre-execution authority
  -> ALLOW | TRANSFORM | HOLD | DENY
  -> controlled actuator
  -> observed physical result
  -> chained evidence / receipts
```

The planner never grants itself permission. Authority evaluates the exact evidence/action pair. HOLD and DENY do not dispatch. ALLOW authorizes the exact proposal. TRANSFORM requires an explicitly authorized physical replacement.

## Mathematical architecture

Let `I` be the governing invariant and `\iota` the value that must survive execution:

$$
I(x_{n+1})=I(x_n)=\iota.
$$

Define

$$
X_I=\{x\in X:I(x)=\iota\}.
$$

An executable controlled transition must remain inside that set:

$$
C_I:X_I\rightarrow X_I.
$$

The planner chooses proposals; authority constrains which proposals may become effects. The invariant is not the planner and does not claim to choose the uniquely optimal action.

## Why this is different

The contribution is an explicit machine-speed authority layer between proposal and effect. That produces visible properties:

1. A learned policy can propose while authority still denies physical handoff.
2. The exact authorized action can be cryptographically bound to the evidence/action identity before dispatch.
3. A blocked command never needs to reach the actuator.
4. Physical execution can be compared against encoder-observed outcome rather than inferred from a send call.
5. Simulation/reference scenarios additionally exercise TRANSFORM, stale evidence, replay and authority-unavailable fail-closed behavior.

## Verified onsite hardware proof

The Intel event machine verified:

- LeRobot 0.6.1 robot-control path;
- Intel Arc B390 through PyTorch XPU for ACT training/inference;
- real SO-101 follower actuation with encoder readback;
- local HTTP pre-execution authority using the repository `ReferenceAuthorityEngine`;
- `workspace_clear=false -> DENY / WORKSPACE_OCCUPIED -> no physical handoff`;
- `workspace_clear=true -> ALLOW / POLICY_SATISFIED` with exact joint-action/envelope preservation;
- one ACT-generated physical action with status `PHYSICALLY_VERIFIED`.

A later governed rollout completed 600 individually evaluated physical steps and reached `MAX_STEPS_REACHED`. This demonstrates endurance of the authority/execution path, **not** task success.

See `docs/ONSITE_EVIDENCE.md` for the proof hash and before/target/after encoder values.

## Intel integration

Verified onsite:

- **Intel Arc B390 / PyTorch XPU** — ACT training and inference;
- **OpenVINO 2026.3** — runtime/integration bring-up;
- **LeRobot 0.6.1** — ACT + SO-101 robot-control path;
- **Physical AI Studio ecosystem** — event workflow/tooling context.

The MVTec PaDiM/OpenVINO artifact was used to prove the inference/runtime path; it was **not** a LEGO detector. Robotics AI Suite is not represented as independently verified in the final physical path.

The authority boundary remains model- and runtime-independent. Swapping detector, policy or robot does not move the final pre-execution decision point.

## Dataset finding and clean-v2 model

The first ten demonstration episodes were not equivalent training examples:

- episodes 0-2: effectively idle;
- episodes 3-4: arm movement with negligible gripper signal;
- episodes 5, 6, 8, 9: strongest manipulation/gripper signal;
- episode 7: substantial arm movement but little gripper movement.

The first ACT model learned a narrow hold attractor from the mixed dataset. Clean-v2 retraining therefore uses episodes `[5,6,8,9]` and `n_action_steps=20` so the policy replans more frequently.

This is an observed data-quality correction, not an authority failure.

## Current demonstration sequence

The verified presentation should show:

### 1. Learned proposal

Show the real robot state/camera input, ACT proposal, bounded six-joint command and execution-envelope hash.

### 2. DENY / no handoff

Set the workspace interlock false and show:

```text
DENY
WORKSPACE_OCCUPIED
authorized_action = None
```

No physical dispatch occurs.

### 3. ALLOW / exact binding

With the workspace actually clear and the operator approving motion, show the authority result:

```text
ALLOW
POLICY_SATISFIED
```

Verify that the returned authorized action preserves the exact joint command and envelope digest.

### 4. Physical outcome

Show before/target/after encoder values and `PHYSICALLY_VERIFIED` for the learned-policy physical step.

### 5. Honest task boundary

Show that the 600-step rollout was governed but did not complete the LEGO task, then explain the clean-v2 data correction. If the clean-v2 autonomous run later succeeds, add that proof as a new result rather than rewriting the earlier evidence.

## Reproducible software rehearsal

The repository also retains a native OpenVINO + MuJoCo rehearsal with reference detector/planner components. It proves deterministic authority semantics, TRANSFORM behavior, stale/replay handling, authority-unavailable fail-closed behavior and receipt-chain logic without requiring event hardware.

Simulation and real-hardware evidence remain clearly labeled and should not be collapsed into one claim.

## Measurements

Keep measurement categories separate:

- ACT inference/device evidence;
- OpenVINO runtime/inference evidence;
- authority-service latency;
- local client elapsed time;
- physical command/encoder convergence;
- test totals and CI results.

Do not present simulator wall-clock time as robot cycle time. Do not convert `MAX_STEPS_REACHED`, `OPERATOR_ABORT`, blocked decisions or unknown outcomes into success.

## Security and failure semantics

The repository is fail-closed at the authority boundary. Malformed service responses, unavailable authority, missing authorized actions, contradictory ALLOW responses, stale/future evidence, replay identity, action/evidence rebinding and corrupted receipts do not become executable commands.

The local dispatcher may remove permission but does not create it. Actuation success is distinguished from dispatch attempt, and observed outcome is preserved separately.

## IP and licensing

This LabLab repository is a greenfield MIT hackathon implementation. External runtimes and packages retain their own licenses.

The proprietary Gatekeeper production/runtime source, proprietary policy corpus, credentials, private infrastructure and other undistributed OASSE technology are not in this repository. The onsite verified hardware path used the repository `ReferenceAuthorityEngine`, not production Gatekeeper.

## Submission package

The final submission should include:

- repository URL accessible to judges;
- exact final commit SHA;
- demo video URL;
- current `submission.json`;
- architecture and judge one-pager;
- CI/test status from the final commit;
- native software rehearsal evidence;
- `docs/ONSITE_EVIDENCE.md`;
- physical proof/video for any autonomous LEGO success if achieved;
- license/provenance statement.

## Claim boundary

Current proven claim: **a trained ACT policy produced a real SO-101 command that passed through an independent pre-execution authority boundary, was exact-bound to its authorization, executed physically and was verified by encoder readback; an explicit denied case produced no physical handoff.**

Current unproven claim: **full autonomous LEGO pick-and-drop task completion.**

Do not collapse reference authority, production Gatekeeper, runtime bring-up models, autonomous task success and hardware-safety certification into one undifferentiated claim.
