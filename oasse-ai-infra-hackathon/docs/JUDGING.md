# Judging Narrative

The technical novelty is not another VLA, another anomaly detector, or another robot safety rule. Intel's stack accelerates perception and physical execution. Gatekeeper adds the independent authority boundary needed when those systems can act at machine speed.

The deeper claim is stronger than "we check a rule before the robot moves." The governing invariant defines the admissible transition space. A proposal is executable only when its resulting transition remains inside that space. In compact form:

$$
X_I=\{x:I(x)=\iota\},
\qquad
C_I:X_I\rightarrow X_I.
$$

This gives the demo a simple five-stage story:

```text
Observe -> Propose -> Project into the admissible state space -> Execute -> Prove
```

The judge should be able to see four facts in under one minute. The model can propose an action. The robot can be capable of performing it. A deterministic independent authority decision can still prevent or constrain it. The system preserves a tamper-evident record that proves what was authorized before the effect and what happened afterward.

The defect case helps distinguish perception from authority. An anomaly detector can report a defect without that fact itself being an authority violation. The planner may propose the reject path, and Gatekeeper may still ALLOW it because the transition remains admissible. **Perception supplies facts. Authority determines admissibility.**

The stale-evidence case is the strongest failure demonstration. The planner's action can remain syntactically valid, the credentials can remain valid, OpenVINO can still work, and the actuator can still work. The only thing that changed is whether the evidence is current enough to justify the transition. That is the Architecture of Authority thesis made physical.

The invariant is also deliberately **not** a planner. It constrains what may happen; it does not claim to select the uniquely optimal action among all admissible choices. That keeps the authority layer separate from the VLA/motion planner and avoids overstating the mathematics.

The key metric remains two-dimensional. We report perception-to-authority end-to-end latency and authority latency separately. In the default reference mode the authority latency is the evaluation time of the MIT-licensed local `ReferenceAuthorityEngine` included in this repository. With `AUTHORITY_MODE=live` it is the authority latency reported by the production Gatekeeper service through `GatekeeperClient`; that service is not included here, and the network round trip is counted in the end-to-end figure. When the service cannot be reached, the fail-closed `HOLD` records the local time elapsed until the failure instead. A fast model with a slow authority layer is not deployable. A fast authority hop hidden inside a slow demo is also not an honest performance claim.

For the deeper technical discussion, use [AUTHORITY_INVARIANT.md](AUTHORITY_INVARIANT.md). The GOI comparison there is methodological only and must not be presented as scientific validation of Gatekeeper.
