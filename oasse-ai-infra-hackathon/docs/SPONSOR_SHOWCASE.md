# Sponsor Showcase Strategy

Winning projects should make the sponsor's technology part of the story the judge remembers, not a logo at the end and not a dependency buried in setup instructions.

For this project, **Intel is the challenge sponsor**. The sponsor story is therefore built into the live proof:

> Intel gives the physical-AI system the ability to see, infer and act at machine speed. Gatekeeper adds an independent machine-speed authority boundary before that capability becomes physical effect.

That makes the sponsor contribution complementary rather than incidental. The demo is stronger because the Intel stack is visible, measurable and necessary to the physical-AI path.

## What should be visible on screen

### Intel Core Ultra

Onsite, show the actual host identity only after it is observed. Do not pre-claim Intel hardware from the software rehearsal. The host is the edge execution surface that keeps perception and control close to the machine.

### OpenVINO

OpenVINO should be one of the most visible sponsor technologies in the demo. Show:

- the OpenVINO runtime version;
- available/selected execution device;
- the actual inference step producing the `EvidenceFrame`;
- inference latency from the frozen run;
- the model/output identity used for the normal and defective cases.

The repository already verifies native compiled OpenVINO inference in the software rehearsal. Onsite, replace the rendered input with the event camera and preserve the same evidence boundary.

### Anomalib

If the onsite track provides or supports the trained Anomalib workflow, make its contribution visual. Show the normal image, defective image, anomaly score and localization. The audience should understand immediately that Intel's anomaly-detection stack produces the physical evidence Gatekeeper later governs.

Do not describe the repository's current deterministic reference detector as a trained Anomalib model. Upgrade that claim only after the onsite trained-model trace exists.

### Physical AI Studio

If used onsite, show it as the integration/workflow surface connecting perception, model and robot execution. Do not merely mention it in the stack slide. Capture one screen or trace that demonstrates its role in the working pipeline.

### Robotics AI Suite

If the event robot runtime is delivered through Intel's Robotics AI Suite, make the transition from authorized action to controlled robot command explicit. The point is not to imply that Gatekeeper replaces Intel's robotics software. Intel supplies the physical-AI execution stack; Gatekeeper governs whether the proposed effect is authorized to proceed.

## The sponsor story in the live demo

The ideal visual sequence is:

```text
Intel camera / edge host
        ↓
OpenVINO + Anomalib evidence
        ↓
Physical AI / VLA proposal
        ↓
Gatekeeper authority boundary
        ↓
Intel robotics execution path
        ↓
post-action observation + receipts
```

At each transition, name the technology that just contributed something visible.

For the **normal object**, call out OpenVINO/Anomalib when the evidence appears. For the **defective object**, show the anomaly localization before the reject proposal. For **TRANSFORM**, show that Intel's physical-AI stack still supplies the proposed capability, while the independent authority layer constrains the exact command that may enter the robot path. For **stale evidence**, emphasize that the perception and robotics stack still work, but the evidence is no longer current enough to justify physical effect.

## Recommended spoken framing

Opening:

> We built this on Intel's Physical AI stack because the interesting problem appears when perception and robotics get fast enough to close the loop. OpenVINO and the Intel physical-AI tooling give the system capability. Gatekeeper decides whether that exact capability is authorized to become physical action now.

During perception:

> This frame is being processed through the Intel inference path. The anomaly result becomes evidence, not authority. The planner can use it to propose an action, but it cannot approve itself.

During execution:

> The authorized action now returns to the physical-AI execution path. Intel handles the machine capability; Gatekeeper handles the permission boundary.

Close:

> Intel makes the physical-AI loop fast enough to matter. We make that machine-speed action governable. Capability proposes. Authority decides.

## Event ecosystem credit

AI Infra Summit, lablab.ai and Native should be credited clearly as the event/hackathon ecosystem that made the build environment and challenge possible. Keep this credit distinct from the technical sponsor proof. The technical demo should not suggest that an organizer supplied a component it did not supply.

## Evidence artifact

Run:

```sh
python scripts/sponsor_showcase.py --output onsite/sponsor-runtime.json
```

This produces a non-actuating runtime record containing the OpenVINO version/device visibility plus installed Anomalib and LeRobot versions when present. It intentionally does **not** claim Intel hardware, trained-model usage, Physical AI Studio usage, Robotics AI Suite usage or robot motion merely because packages are installed.

## Greenfield rule

Do not copy sponsor logos, screenshots, code, model weights or branded assets into the MIT repository unless their reuse terms are explicitly cleared. We can showcase the sponsors by naming their technology, recording runtime evidence and demonstrating what it does. That is stronger evidence than decorative assets and preserves the repository's greenfield MIT boundary.
