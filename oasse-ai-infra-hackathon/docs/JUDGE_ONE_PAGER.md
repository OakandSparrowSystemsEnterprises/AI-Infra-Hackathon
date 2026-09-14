# Judge One-Pager

## Gatekeeper: Pre-Execution Security for Physical AI

**Thesis:** Capability proposes. Authority decides. Execution follows authority, not capability.

### The problem

Physical AI is getting fast enough that perception, planning and action can collapse into one machine-speed loop. That loop still needs a separate answer to a basic question: *is this exact action authorized now, using this exact evidence, for this actor and environment?*

### What we built

```text
camera -> perception -> evidence -> VLA proposal -> Gatekeeper -> actuator -> observed outcome
                                      |               |
                                      |               +-> ALLOW / TRANSFORM / HOLD / DENY
                                      +------------------ exact evidence/action binding
```

Gatekeeper sits immediately before physical effect. It is independent of the detector, VLA and robot runtime.

### The five proof points

1. **Fresh valid action:** ALLOW and execute.
2. **Overspeed action:** TRANSFORM and execute only the constrained replacement.
3. **Stale evidence:** HOLD with zero new movement.
4. **Authority unavailable:** HOLD instead of bypassing governance.
5. **Receipts:** bind observation, proposal, authority decision, dispatch and observed result.

### Why it matters

Monitoring after the fact cannot prevent an unauthorized state transition. Model alignment alone does not establish actor-specific, time-specific execution authority. Robot capability alone does not answer whether the action is permitted. Gatekeeper makes authorization a first-class infrastructure layer.

### Intel fit

OpenVINO and the event Physical AI stack accelerate perception and robotic capability. Gatekeeper governs the final transition from proposed action to physical effect without requiring a specific model family.

### Reproducibility

The repository includes a native OpenVINO + native MuJoCo software rehearsal, deterministic failure scenarios, CI, evidence bundles, receipt verification and onsite integration tooling. Hardware-specific claims remain false until verified onsite.

### IP and licensing

The LabLab repository is greenfield MIT code. External runtimes remain separately licensed dependencies. Proprietary Gatekeeper production source and policy corpus are not distributed; the live service is reached through the repository's MIT HTTP adapter.

### What to watch in the demo

Watch the stale-evidence case. Nothing else is broken: the planner still proposes and the actuator is still capable. The system stops because the evidence is no longer current enough to justify the physical transition. That is the authority boundary made visible.
