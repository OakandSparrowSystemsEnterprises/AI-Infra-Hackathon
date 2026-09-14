# Final Draft: Gatekeeper for Physical AI

## Project title

**Gatekeeper: Pre-Execution Security for Physical AI**

## Team

Oak & Sparrow Systems Enterprise LLC

## Challenge

Intel Physical AI Challenge

## One-line thesis

**Capability proposes. Authority decides. Execution follows authority, not capability.**

## Problem

Physical-AI systems are becoming fast enough to perceive, plan and act with very little human friction. That speed creates a missing control boundary. A model may be capable of generating a movement, and a robot may be technically capable of executing it, without that movement being authorized for the current actor, evidence, environment, timing or policy state.

Most safety and governance approaches observe, log or filter around the model. This project places an independent deterministic authority decision immediately before physical effect. The execution path therefore distinguishes *what the system can do* from *what it is permitted to do now*.

## Solution

The integration uses a strict sequence:

```text
camera / sensor evidence
  -> perception
  -> EvidenceFrame
  -> VLA / planner proposal
  -> ProposedAction
  -> Gatekeeper authority
  -> ALLOW | TRANSFORM | HOLD | DENY
  -> controlled actuator
  -> outcome observation
  -> chained receipts
```

The planner never grants itself permission. Gatekeeper evaluates the exact evidence/action pair and returns one of four outcomes:

- **ALLOW**: execute the proposal exactly as submitted.
- **TRANSFORM**: execute only the explicitly authorized physical replacement.
- **HOLD**: do not execute; wait for better evidence, restored authority or another required condition.
- **DENY**: do not execute because policy or identity state rejects the transition.

The final dispatch gate independently checks binding, evidence age, replay state, scene state and receipt integrity before allowing an actuator call.

## Why this is different

The novelty is not another VLA, anomaly detector or robot rule set. The contribution is an explicit machine-speed authority layer between proposal and effect.

That distinction produces several properties that are visible in the demo:

1. A valid-looking action can still be stopped because its evidence is stale.
2. An overspeed proposal can be transformed into a constrained authorized action without allowing the original command to slip through.
3. An unavailable authority service fails closed instead of falling back to ungoverned execution.
4. Replayed evidence cannot be used to authorize another physical effect.
5. The system records what was observed, what was proposed, what was authorized, what was dispatched and what was observed afterward.

## Sponsor showcase: Intel should be visible in the proof

Intel is not treated as a logo or a package dependency in this project. The sponsor story is part of the architecture and live demonstration.

**Intel supplies the physical-AI capability surface. Gatekeeper supplies the independent authority surface.**

The onsite story should visibly connect:

```text
Intel edge/physical-AI host
  -> OpenVINO inference
  -> Anomalib anomaly evidence when the trained workflow is available
  -> Physical AI / VLA workflow
  -> Gatekeeper authority
  -> Intel robotics execution path
  -> verified physical outcome
```

When each Intel component is used, show what it contributes. Put the OpenVINO runtime/device and inference result on screen. Show anomaly score/localization for the defect case. If Physical AI Studio and Robotics AI Suite are used onsite, show their actual workflow/runtime role rather than only naming them on a slide.

The framing is complementary: Intel makes perception and physical execution fast and practical; Gatekeeper makes the resulting machine-speed action governable. See `docs/SPONSOR_SHOWCASE.md` for the exact presentation and evidence plan.

## Intel integration

The software rehearsal exercises native OpenVINO inference and native MuJoCo dynamics. The onsite target is the event-provided Intel Physical AI stack, including the available camera path, OpenVINO/Anomalib detector workflow, LeRobot or event-selected VLA path, and robot runtime.

The Intel side supplies perception acceleration and physical-AI capability. Gatekeeper remains independent of the model and runtime. Swapping the detector, VLA or robot does not move the authority boundary.

## Current verified software rehearsal

The repository contains a reproducible software rehearsal that uses:

- rendered RGB evidence;
- compiled native OpenVINO inference;
- an explicitly labeled reference detector;
- a scripted sorting planner;
- the MIT-licensed local reference authority engine;
- native MuJoCo physics;
- an idealized Cartesian suction constraint;
- post-action task verification;
- chained decision, outcome and verification evidence.

This rehearsal proves the integration architecture and failure semantics. It does **not** claim that SO-101 or other event hardware, a trained Anomalib detector, a trained VLA or production Gatekeeper have already been verified. Those fields remain pending until onsite evidence exists.

## Demonstration sequence

The preferred live demonstration is deliberately short and visual.

### 1. Normal object

Show the camera frame and explicitly identify the Intel/OpenVINO inference path. Show the detector evidence and proposed accept action. Gatekeeper returns ALLOW. The robot performs the permitted action. A new observation confirms the object reached the expected destination. Show the linked decision and outcome receipts.

### 2. Defective object

Show the visible defect and the anomaly score/localization from the onsite detector workflow. The planner proposes the reject destination. Gatekeeper authorizes the exact action. The robot routes the object to reject and the post-action observation confirms the result.

### 3. Overspeed proposal

Show a proposal above the configured movement limit. Gatekeeper returns TRANSFORM with a lower authorized speed. Demonstrate that only the transformed action reaches the actuator and report the measured execution speed separately from the proposed speed.

### 4. Stale evidence

Reuse an otherwise valid proposal after its evidence exceeds the configured freshness window. The Intel perception and robotics capabilities remain available, but the evidence is no longer current enough to justify the action. Gatekeeper/dispatch HOLD the action and no movement starts.

### 5. Authority unavailable

Show that loss of the authority endpoint produces HOLD with no actuator call. The failure is visible and receipt-bound rather than silently bypassed.

## What judges should see in under one minute

Intel's stack gives the system the ability to perceive and act at machine speed. The model proposes. The robot is capable. An independent authority layer can still allow, constrain or stop the physical effect. The system then proves which action was authorized before execution and records what happened afterward.

## Measurements

Report measurements from the frozen final run only. Keep these categories separate:

- OpenVINO/perception inference latency;
- authority-service latency;
- client/network elapsed time;
- perception-to-authority end-to-end latency;
- physical execution measurements;
- post-action verification result;
- test totals and failures from the exact final commit.

Do not describe simulator wall-clock time as real robot cycle time. Do not convert UNKNOWN or partial physical outcomes into successes.

## Security and failure semantics

The repository is fail-closed at the authority boundary. Malformed service responses, unreachable authority, missing transformed actions, contradictory ALLOW responses, stale or future evidence, replayed capture identity, action/evidence rebinding, corrupted receipts and incomplete model output do not become executable commands.

The local dispatcher can remove permission but never create permission. `dispatch_attempted` is distinct from `executed`, and actuator errors produce an unknown outcome rather than an invented successful execution.

## Greenfield and license statement

This LabLab repository is a greenfield hackathon implementation licensed under MIT. Everything authored and committed in this repository is intended to be distributable under the repository MIT License. External runtimes and packages remain separately licensed dependencies and are not vendored or relicensed here.

No source, assets, notebooks or model weights from the external LeRobot/MuJoCo tutorial are included. The tutorial was used only as a workflow reference. The implementation in this repository was independently authored against the project's own provider contracts.

The proprietary Gatekeeper production/runtime source, proprietary policy corpus, credentials, private infrastructure and other undistributed OASSE technology are not in this repository. The live build consumes the production authority service only through the MIT-licensed HTTP adapter.

## Event ecosystem credit

AI Infra Summit, lablab.ai and Native are credited as the event/hackathon ecosystem that created the build environment and sponsor challenge. Keep this separate from the technical sponsor proof so the final presentation accurately attributes each party's role.

## Submission package

A final submission should include:

- repository URL accessible to judges;
- exact final commit SHA;
- demo video URL;
- concise project description;
- architecture diagram or architecture section;
- sponsor runtime evidence from `scripts/sponsor_showcase.py`;
- reproducible run instructions;
- final test count and CI status;
- native software rehearsal evidence;
- onsite acceptance evidence for camera, trained detector, trained VLA, final pre-send interception and hardware runs;
- production Gatekeeper contract probe if used in the live demonstration;
- normal, defective, transformed and no-motion failure evidence;
- license/provenance statement.

## Claim boundary

The strongest version of the project is the version supported by the final evidence. Before onsite hardware traces exist, describe the current state as a complete software rehearsal prepared for hardware binding. After hardware runs succeed, update only the claims directly proven by those traces. Do not collapse simulation, operator attestation and production-service verification into one undifferentiated claim.
