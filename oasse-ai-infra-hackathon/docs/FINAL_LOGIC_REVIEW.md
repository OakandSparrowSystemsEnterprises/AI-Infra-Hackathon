# Final Logic and Hardening Review

## Scope

This is the final pre-onsite adversarial review of the governed execution architecture. It does not claim physical-hardware validation. It asks a narrower question:

> **Given the repository's declared trust boundary, can an unauthorized, stale, rebound, replayed, malformed, ambiguously acknowledged, or unbounded remote action become a confirmed physical effect through the governed path?**

After this pass, the tested software path fails closed for those cases unless an explicitly documented trust assumption is violated.

## Architectural invariants

1. **Capability cannot self-authorize.** Perception and planning produce facts and proposals only.
2. **Evidence and action identity remain bound.** Authority must decide against the exact isolated evidence/action snapshots presented for evaluation.
3. **ALLOW is identity.** ALLOW may execute only the unchanged proposal.
4. **TRANSFORM is substitution.** Only the explicit authorized replacement may execute; actor, action and evidence identity cannot be rebound.
5. **HOLD and DENY are non-effects.** Neither reaches the actuator.
6. **Freshness is checked again at dispatch.** A decision valid during evaluation can still lose launch authority.
7. **Dispatch is one-shot.** Evidence/action identities are atomically reserved before actuator invocation and are not automatically retried after uncertain effects.
8. **Execution confirmation is bound to the command.** `EXECUTED` is accepted only when the actuator explicitly acknowledges the matching action ID.
9. **Actuator acknowledgement is not task completion.** Execution and postcondition verification remain separate records.
10. **UNKNOWN remains unknown.** Exceptions, malformed acknowledgements and partial effects never become successful execution.
11. **Receipt integrity is append-only and externally isolated.** Public receipt objects cannot mutate internal chain state.
12. **Remote authority input is bounded.** Oversized, malformed, contradictory or insecurely transported authority traffic cannot become an executable command.

## Final hardening changes

### Pooled, protected authority transport

`GatekeeperClient` creates one pooled `httpx.Client` lazily on the first authority call and reuses it. Repeated decisions therefore avoid repeated TCP/TLS setup while client-construction failures still fail closed.

Production authority endpoints require HTTPS. Plain HTTP is accepted only for explicitly enabled loopback contract tests. `GATEKEEPER_TIMEOUT_S` is configurable and defaults to **0.25 seconds** so the authority call fails before the repository's default **500 ms** evidence-freshness window is exhausted. That default is an integration choice, not a universal production SLA; onsite measurements must validate the deployed network and service.

Request bodies are bounded. Response bodies are consumed through a bounded stream and rejected before JSON parsing if they exceed the limit, so the response limit is an actual memory boundary rather than a check performed after an arbitrarily large body has already been buffered.

Service-controlled narrative fields are bounded and credential-redacted. Unknown informational response fields are ignored rather than recursively traversed. Accepted textual action fields that echo the bearer credential make the response invalid rather than allowing the secret into executable state.

### Snapshot isolation without redundant hot-path hashing

Cross-plane mutation protection uses validated detached snapshots plus direct structural equality. The planner, authority adapter and actuator receive copies at the trust boundaries; the local canonical baseline remains separate.

This preserves mutation detection while removing repeated canonical JSON serialization and SHA-256 passes from the authority hot path and from every guarded physics step. Cryptographic hashing remains where it provides durable value: captured-evidence identity, receipt integrity and exported evidence verification.

### Constant-time receipt execution gate

The previous implementation re-walked the growing receipt chain before effects. Internal receipt records are now immutable and private, while callers receive detached snapshots. The pre-effect integrity check validates the chain tail and adjacent link in **O(1)**. Full **O(n)** verification remains available for `/health`, export and evidence review.

Receipt identity is included in the hashed envelope, so changing a receipt ID invalidates the record. This is hash-chain integrity, not a digital signature or proof of sensor authenticity.

### Atomic dispatch reservation and single-sample freshness checks

Replay, sequence, scene and freshness checks share one locked dispatch-guard path. `reserve()` atomically rechecks launch conditions and consumes the evidence/action identities immediately before actuator invocation.

A monotonic lease prevents wall-clock adjustment from extending already-issued freshness. The per-step guarded actuator path can recheck that lease without repeated canonical hashing.

### Explicit execution acknowledgement binding

An actuator may report `EXECUTED` only if its result explicitly contains the same `action_id` that was sent. A missing or mismatched action ID becomes `UNKNOWN` with `ACTUATOR_RESULT_BINDING_MISMATCH`; it is not counted as confirmed execution.

The outcome receipt still records that dispatch was attempted, preserving uncertainty rather than inventing success or non-execution.

### Bounded runtime telemetry

Latency metrics now keep a bounded rolling window of **4096 samples** while lifetime run and verdict counters continue. A long-running service therefore does not grow metric sample storage without bound merely because the demo remains online.

### Stricter live contract

Live authority timestamps must be exact non-negative 64-bit integers. Reason-code collections and control strings are bounded. Transformed trajectories must be bounded XYZ paths. Oversized requests/responses, invalid response structure, contradictory ALLOW payloads, invalid TRANSFORM payloads and authority outages fail closed.

## Latency discipline

CI runs `scripts/benchmark_hot_path.py` as a regression guard. It separately measures:

- deterministic local reference-authority evaluation; and
- the complete synthetic governed dispatch path while the receipt chain grows.

The enforced CI budgets are:

- reference authority p95 **< 0.25 ms**;
- synthetic governed pipeline p95 **< 3.0 ms**.

These are deliberately generous regression ceilings, not product benchmark claims. The benchmark excludes network transit, OpenVINO inference and physical robot time. Production Gatekeeper latency, onsite inference latency and robot timing must be reported independently from the actual frozen onsite run.

The architecture optimizes only work that does not weaken the authority boundary. A lower latency number is not accepted if it removes binding, freshness, replay, receipt or outcome-integrity checks.

## Review matrix

| Review question | Current software answer |
| --- | --- |
| Can the planner approve itself? | No. Proposal and authority planes are separate. |
| Can ALLOW rewrite motion? | No. ALLOW requires the unchanged proposal. |
| Can TRANSFORM fall back to the original action? | No. Only the explicit authorized replacement is dispatchable. |
| Can stale/future evidence launch? | No. Evaluation/dispatch freshness checks fail closed. |
| Can the same evidence/action dispatch twice in-session? | No. Atomic reservation blocks replay. |
| Can an authority response rebind actor/action/evidence identity? | No. Binding changes fail closed. |
| Can an oversized remote response exhaust the declared parser budget? | It is rejected while streaming before JSON parse. |
| Can an actuator say only `EXECUTED` without identifying the command? | No. Matching `action_id` is required for confirmed execution. |
| Can a caller mutate the internal receipt chain via a returned payload? | No. Public receipts are detached snapshots. |
| Does every hot-path decision reverify the entire receipt history? | No. O(1) tail gate; O(n) full audit remains available. |
| Can metric samples grow forever? | No. Rolling latency samples are bounded. |
| Does this prove hardware safety? | No. Hardware-layer guarantees remain onsite/lower-layer work. |

## What remains outside the proof

A rigorous reviewer should still reject any claim that this repository alone proves:

- camera/source authenticity;
- durable replay and receipt state across process restart;
- OS/device-level isolation from malicious code with direct actuator access;
- physical braking or emergency-stop guarantees;
- collision avoidance beyond the declared integration checks;
- production Gatekeeper service identity without deployment attestation;
- trained Anomalib/VLA behavior until onsite traces exist;
- real robot safety, cycle time or control-loop timing before hardware runs;
- network or production authority latency from the local CI benchmark;
- signed/authenticated telemetry merely because receipt hashes verify.

Those are explicit integration or lower-layer responsibilities, not hidden omissions.

## Review conclusion

The architecture is intentionally narrow and compositional. **INTEL's Physical AI stack supplies perception and execution capability. GATEKEEPER supplies the independent deterministic pre-execution authority boundary.** The governed path isolates inputs, evaluates exact bindings, can transform or withhold authority, rechecks launch conditions, atomically reserves a transition once, binds confirmed execution to the exact command, records uncertain outcomes honestly, and separately verifies the observed postcondition.

The mathematical layer describes that structure as an invariant-preserving transition system. The code enforces the concrete contract that the demo can actually prove. The remaining unknowns require the onsite machine, camera, trained models, deployed Gatekeeper service and robot, not another speculative software layer.
