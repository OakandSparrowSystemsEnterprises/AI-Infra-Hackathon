# Final Logic and Hardening Review

## Scope

This pass is the final pre-onsite adversarial review of the governed execution architecture. It does not claim physical hardware validation. It asks a narrower question: **given the repository's declared trust boundary, can an unauthorized, stale, rebound, replayed, malformed, or ambiguously reported action become a confirmed physical effect through the governed path?**

The answer after this pass is: not through the tested software path without violating an explicitly documented trust assumption.

## Architectural invariants

1. **Capability cannot self-authorize.** Perception and planning produce facts/proposals only.
2. **Evidence and action identity remain bound.** The authority result must refer to the exact isolated evidence/action snapshots presented for evaluation.
3. **ALLOW is identity.** An ALLOW may execute only the unchanged proposal.
4. **TRANSFORM is substitution.** Only the explicit authorized replacement may execute, and it must differ in a physical field without rebinding actor/action/evidence identity.
5. **HOLD and DENY are non-effects.** Neither reaches the actuator.
6. **Freshness is checked again at dispatch.** A decision that was valid when evaluated can still lose launch authority.
7. **Dispatch is one-shot.** Evidence/action identities are atomically reserved before actuator invocation and are not automatically retried after uncertain effects.
8. **Actuator acknowledgement is not task completion.** Execution and postcondition verification are separate records.
9. **UNKNOWN remains unknown.** Exceptions, malformed acknowledgements and partial effects never become successful execution.
10. **Receipt integrity is append-only and externally isolated.** Callers receive detached receipt snapshots and cannot mutate the internal chain by editing a returned object.

## Final hardening changes

### Connection pooling and transport protection

`GatekeeperClient` lazily creates one pooled `httpx.Client` on the first authority call and reuses it thereafter. That preserves fail-closed handling of client-construction failures while avoiding repeated TCP/TLS setup on the live decision path. Production authority endpoints require HTTPS; plain HTTP is accepted only for explicitly enabled loopback contract tests. Request and response bodies are size bounded, and service-controlled narrative fields are credential-redacted before they can enter receipts or reports.

### Snapshot isolation instead of repeated cryptographic fingerprints

Cross-plane mutation protection uses detached validated snapshots plus direct structural equality. The planner, authority adapter and actuator receive copies, never the nested structures held as the local canonical baseline. The final optimization removes redundant private-to-private copies while preserving a detached copy at every trust-boundary crossing. Cryptographic hashing remains where it belongs: evidence identity, receipts and exported evidence integrity.

### Constant-time receipt gate

The previous implementation fully re-walked the growing receipt chain before effects. Public receipts are detached from private immutable stored records, so a consumer cannot corrupt chain state through a returned payload. The hot-path integrity gate validates the immutable tail and adjacent link in O(1); full O(n) verification remains available at `/health`, receipt export and evidence verification. Receipt identity is hash-bound.

### Single-sample dispatch validation

Replay/scene/freshness checking performs one freshness sample per guard call and atomically reserves evidence/action identity immediately before actuator invocation.

### Stricter live contract

Live authority timestamps must be exact non-negative 64-bit integers, reason-code collections and control strings are bounded, transformed trajectories must be bounded XYZ paths, and oversized or malformed authority traffic fails closed rather than being coerced into execution.

## Latency discipline

CI runs `scripts/benchmark_hot_path.py` on the reference path. It separately measures deterministic reference authority evaluation and complete synthetic governed dispatch while the receipt chain grows. The budgets are regression guards, not product benchmark claims:

- reference authority p95 below **0.25 ms** on the GitHub runner;
- synthetic governed pipeline p95 below **3.0 ms** on the GitHub runner.

The benchmark excludes network transit, OpenVINO inference and physical robot time. Onsite measurements must report those components separately.

## What remains outside the proof

A rigorous review should still reject any claim that this repository alone proves camera/source authenticity, durable replay protection across restart, OS-level isolation from malicious code with direct actuator access, physical braking or emergency-stop guarantees, collision avoidance beyond declared checks, production Gatekeeper identity without deployment attestation, trained Anomalib/VLA behavior before onsite traces, or real robot timing and safety performance.

Those are explicit integration or lower-layer responsibilities, not hidden assumptions.

## Review conclusion

The architecture is intentionally narrow and compositional. Intel's Physical AI stack supplies perception and execution capability. Gatekeeper supplies a deterministic pre-execution authority boundary. The governed path isolates inputs, evaluates exact bindings, can transform or withhold authority, rechecks launch conditions, reserves a transition once, records uncertain outcomes honestly, and separately verifies the observed postcondition.

The mathematics describes that structure as an invariant-preserving transition system; the code enforces the concrete contract that the demo can actually prove.
