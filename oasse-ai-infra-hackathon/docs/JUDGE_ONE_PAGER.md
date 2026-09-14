# Judge One-Pager

## **INTEL® PHYSICAL AI CHALLENGE**

### Gatekeeper: Pre-Execution Security for Physical AI

**INTEL® CORE™ ULTRA · OPENVINO™ · ANOMALIB · PHYSICAL AI STUDIO · ROBOTICS AI SUITE**

Built for **AI INFRA SUMMIT 2026** with **lablab.ai** and **Native**.

**Thesis:** Capability proposes. Authority decides. Execution follows authority, not capability.

### The problem

Physical AI is getting fast enough that perception, planning and action can collapse into one machine-speed loop. That loop still needs a separate answer to a basic question: *is this exact action authorized now, using this exact evidence, for this actor and environment?*

### What we built

```text
Intel perception -> evidence -> VLA proposal -> Gatekeeper -> Intel robotics path -> outcome
                                           |               |
                                           |               +-> ALLOW / TRANSFORM / HOLD / DENY
                                           +------------------ exact evidence/action binding
```

Gatekeeper sits immediately before physical effect. It is independent of the detector, VLA and robot runtime.

### The deeper architecture

Authority defines the admissible transition space:

$$
C_I:X_I\rightarrow X_I,
\qquad
I(C_I(x))=I(x)=\iota.
$$

The planner chooses proposals. Authority determines whether the exact transition is executable now.

### The five proof points

1. **Fresh valid action:** ALLOW and execute.
2. **Overspeed action:** TRANSFORM and execute only the constrained replacement.
3. **Stale evidence:** HOLD with zero new movement.
4. **Authority unavailable:** HOLD instead of bypassing governance.
5. **Receipts:** bind observation, proposal, authority decision, dispatch and observed result.

### Why it matters

Monitoring after the fact cannot prevent an unauthorized state transition. Model alignment alone does not establish actor-specific, time-specific execution authority. Robot capability alone does not answer whether the action is permitted. Gatekeeper makes authorization a first-class infrastructure layer.

### **Intel fit**

**OPENVINO** accelerates inference and is already verified in the native software rehearsal. **ANOMALIB**, **PHYSICAL AI STUDIO**, **ROBOTICS AI SUITE** and **INTEL CORE ULTRA** are surfaced explicitly when their onsite use is actually verified. Gatekeeper governs the final transition from proposed action to physical effect without requiring a specific model family.

### Reproducibility

The repository includes native OpenVINO + native MuJoCo rehearsal, deterministic failure scenarios, CI, evidence bundles, receipt verification and onsite integration tooling. Hardware-specific claims remain false until verified onsite.

### IP and licensing

The LabLab repository is greenfield MIT code. External runtimes remain separately licensed dependencies. Proprietary Gatekeeper production source and policy corpus are not distributed; the live service is reached through the repository's MIT HTTP adapter.

### What to watch in the demo

Watch the stale-evidence case. Nothing else is broken: OpenVINO still works, the planner still proposes and the actuator is still capable. The system stops because the evidence is no longer current enough to justify the physical transition. That is the authority boundary made visible.
