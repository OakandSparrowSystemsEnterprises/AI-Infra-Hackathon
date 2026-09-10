# Judging Narrative

The technical novelty is not another VLA or another robot safety rule. Intel's stack accelerates perception and physical execution. Gatekeeper adds the independent authority boundary needed when those systems can act at machine speed.

The judge should be able to see four facts in under one minute. The model can propose an action. The robot can be capable of performing it. A deterministic independent authority decision can still prevent or constrain it. The system preserves a tamper-evident record that proves what was authorized before the effect and what happened afterward.

The key metric is therefore two-dimensional. We report perception-to-authority end-to-end latency and the authority latency separately. In the default reference mode the authority latency is the evaluation time of the MIT-licensed local `ReferenceAuthorityEngine` included in this repository. With `AUTHORITY_MODE=live` it is the authority latency reported by the production Gatekeeper service through `GatekeeperClient`; that service is not included here, and the network round trip is counted in the end-to-end figure. A fast model with a slow authority layer is not deployable. A fast authority hop hidden inside a slow demo is also not an honest performance claim.

The strongest failure demonstration is stale evidence. The planner's action is still syntactically valid, the credentials are still valid, and the actuator still works. The only thing that changed is whether the evidence is current enough to justify the transition. That is the Architecture of Authority thesis made physical.
