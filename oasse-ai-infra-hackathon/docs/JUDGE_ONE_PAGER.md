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
Intel perception -> evidence -> VLA proposal -> [optional Tenki derived evidence] -> Gatekeeper -> Intel robotics path -> outcome
                                                       authority=false          |
                                                                                +-> ALLOW / TRANSFORM / HOLD / DENY
```

Gatekeeper sits immediately before physical effect. It is independent of the detector, VLA, optional derived-compute plane and robot runtime. Tenki, when enabled, is explicitly non-authoritative and contributes only evidence bound to the exact proposal.

### The deeper architecture

Authority defines the admissible transition space:

$$
C_I:X_I\rightarrow X_I,
\qquad
I(C_I(x))=I(x)=\iota.
$$

The planner chooses proposals. Optional compute may derive evidence. Authority determines whether the exact transition is executable now.

### The five core proof points

1. **Fresh valid action:** ALLOW and execute.
2. **Overspeed action:** TRANSFORM and execute only the constrained replacement.
3. **Stale evidence:** HOLD with zero new movement.
4. **Authority unavailable:** HOLD instead of bypassing governance.
5. **Receipts:** bind observation, proposal, authority decision, dispatch and observed result.

If the current Tenki runtime is live, show an additional supporting proof: the exact evidence/action artifact receives a `claim_hash` with `authority=false`, and that `PRE_AUTHORITY_EVIDENCE` receipt precedes the Gatekeeper decision. Do not show historical Tenki runtime evidence as if it came from the current event run.

### Why it matters

Monitoring after the fact cannot prevent an unauthorized state transition. Model alignment alone does not establish actor-specific, time-specific execution authority. Robot capability alone does not answer whether the action is permitted. Derived compute alone does not answer it either. Gatekeeper makes authorization a first-class infrastructure layer.

### **Intel fit**

**OPENVINO** accelerates inference and is already verified in the native software rehearsal. **ANOMALIB**, **PHYSICAL AI STUDIO**, **ROBOTICS AI SUITE** and **INTEL CORE ULTRA** are surfaced explicitly when their onsite use is actually verified. Gatekeeper governs the final transition from proposed action to physical effect without requiring a specific model family.

### Tenki fit

Tenki is optional isolated compute before authority. The adapter hashes the exact proposal/evidence artifact and accepts only a bounded claim that binds back to that artifact, requested effect and principal while explicitly remaining `authority=false`. It cannot return an executable verdict or authorized action. The default `TENKI_MODE=off` preserves the original path; `observe` adds evidence opportunistically; `required` fails closed before Gatekeeper when the declared evidence requirement is not met.

### Reproducibility

The repository includes native OpenVINO + native MuJoCo rehearsal, deterministic failure scenarios, CI, evidence bundles, receipt verification, Tenki contract tests and onsite integration tooling. Hardware-specific and live-Tenki claims remain false until verified onsite.

### IP and licensing

The LabLab repository is greenfield MIT code. External runtimes remain separately licensed dependencies. Proprietary Gatekeeper production source and policy corpus are not distributed; the live service is reached through the repository's MIT HTTP adapter. Tenki platform source is not vendored.

### What to watch in the demo

Watch the stale-evidence case. Nothing else is broken: OpenVINO still works, the planner still proposes and the actuator is still capable. The system stops because the evidence is no longer current enough to justify the physical transition. That is the authority boundary made visible.
