# **SPONSOR SHOWCASE STRATEGY**

## **INTEL® PHYSICAL AI CHALLENGE**

### **INTEL® CORE™ ULTRA · OPENVINO™ · ANOMALIB · PHYSICAL AI STUDIO · ROBOTICS AI SUITE**

Winning projects should make the sponsor's technology part of the story the judge remembers, not a logo at the end and not a dependency buried in setup instructions.

For this project, **INTEL is the challenge sponsor**. The sponsor story is therefore built into the architecture, runtime evidence and live proof:

> **Intel gives the physical-AI system the ability to see, infer and act at machine speed. Gatekeeper adds an independent machine-speed authority boundary before that capability becomes physical effect.**

That makes the sponsor contribution complementary rather than incidental. The demo is stronger because the Intel stack is visible, measurable and necessary to the Physical AI path.

## What must be visible on screen

### **INTEL® CORE™ ULTRA**

Onsite, show the actual host identity only after it is observed. Do not pre-claim Intel hardware from the software rehearsal. The host is the edge execution surface that keeps perception and control close to the machine.

### **OPENVINO™**

OpenVINO should be one of the most visible sponsor technologies in the demo. Show:

- OpenVINO runtime version;
- available and selected execution device;
- actual inference producing the `EvidenceFrame`;
- inference latency from the frozen run;
- model/output identity used for normal and defective cases.

The repository already verifies native compiled OpenVINO inference in the software rehearsal. Onsite, replace rendered input with the event camera and preserve the same evidence boundary.

### **ANOMALIB**

When the onsite trained workflow is verified, make its contribution visual. Show the normal image, defective image, anomaly score and localization. The audience should understand immediately that the anomaly workflow supplies physical facts that Gatekeeper later governs.

Do not describe the repository's current deterministic reference detector as a trained Anomalib model. Upgrade that claim only after the onsite trained-model trace exists.

### **PHYSICAL AI STUDIO**

If used onsite, show it as the integration/workflow surface connecting perception, model and robot execution. Capture one screen or trace that demonstrates its actual role in the working pipeline.

### **ROBOTICS AI SUITE**

If the event robot runtime is delivered through Intel's Robotics AI Suite, make the transition from authorized action to controlled robot command explicit. Gatekeeper does not replace Intel's robotics software. **Intel supplies the physical-AI execution stack; Gatekeeper governs whether the proposed effect is authorized to proceed.**

## Sponsor-visible architecture

```text
┌───────────────────────────────────────────────────────────────────┐
│                           **INTEL**                               │
│ Core Ultra -> OpenVINO -> Anomalib -> Physical AI -> Robotics    │
└───────────────────────────────┬───────────────────────────────────┘
                                │ evidence + proposal
                                v
                  ┌────────────────────────────┐
                  │ **GATEKEEPER AUTHORITY**   │
                  │ ALLOW / TRANSFORM          │
                  │ HOLD / DENY                │
                  └──────────────┬─────────────┘
                                 │ authorized action only
                                 v
                  Intel robotics execution path
                                 │
                                 v
                     observed outcome + receipts
```

At each transition, name the technology that just contributed something visible.

For the **normal object**, call out OpenVINO when evidence appears. For the **defective object**, show Anomalib score/localization if the trained workflow is live. For **TRANSFORM**, show that Intel's Physical AI stack still supplies capability while Gatekeeper constrains the exact command entering the robot path. For **stale evidence**, emphasize that the Intel perception and robotics stack still work; the evidence is simply no longer current enough to authorize the transition.

## Spoken framing

Opening:

> We built this on **Intel's Physical AI stack** because the interesting governance problem appears when perception and robotics get fast enough to close the loop. **OpenVINO** and Intel's Physical AI tooling give the system capability. Gatekeeper decides whether that exact capability is authorized to become physical action now.

During perception:

> This frame is being processed through **OpenVINO**. The anomaly result becomes evidence, not authority. The planner can use it to propose an action, but it cannot approve itself.

During execution:

> The authorized action now returns to the **Intel robotics execution path**. Intel handles the machine capability; Gatekeeper handles the permission boundary.

Close:

> **Intel makes the Physical AI loop fast enough to matter. Gatekeeper makes machine-speed action governable. Capability proposes. Authority decides.**

## **AI INFRA SUMMIT 2026 ecosystem recognition**

The project is built for **AI INFRA SUMMIT 2026** with **lablab.ai** and **Native** as the hackathon ecosystem.

AI Infra Summit's current Diamond Partners are:

**AMBarella · AMD · AWS · HCLTech · INTEL · ORACLE · QUALCOMM**

This is event-level recognition only. It does not imply that every Diamond Partner supplied technology used in this project. **INTEL** remains the challenge sponsor and the sponsor whose technology is part of this project's technical proof.

## Evidence artifact

Run:

```sh
python scripts/sponsor_showcase.py --output onsite/sponsor-runtime.json
```

This produces a non-actuating runtime record containing OpenVINO version/device visibility plus installed Anomalib and LeRobot versions when present. It intentionally does **not** claim Intel hardware, trained-model usage, Physical AI Studio usage, Robotics AI Suite usage or robot motion merely because packages are installed.

## Greenfield rule

Do not copy sponsor logos, screenshots, code, model weights or branded assets into the MIT repository unless their reuse terms are explicitly cleared. We showcase sponsors by naming their technology, recording runtime evidence and demonstrating what it does. That is stronger evidence than decorative assets and preserves the repository's greenfield MIT boundary.

Public attribution sources:

- Intel AI Infra Summit / Physical AI Challenge: https://www.intel.com/content/www/us/en/events/ai-infra-summit.html
- Intel Newsroom: https://newsroom.intel.com/artificial-intelligence/intel-at-ai-infra-summit-2026
- AI Infra Summit sponsors: https://www.ai-infra-summit.com/sponsors
