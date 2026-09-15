# Tenki Integration: Non-Authoritative Pre-Authority Compute

Tenki is integrated as an **optional isolated compute/evidence plane before Gatekeeper**, not as a second authority system and not as a required robot transport.

The architecture is:

```text
Intel camera / OpenVINO / Anomalib
                |
                v
          EvidenceFrame
                |
Physical AI Studio / LeRobot / VLA
                |
                v
          ProposedAction
                |
                v
             TENKI
     isolated derived evidence
         authority = false
                |
                v
           GATEKEEPER
    sole execution authority
 ALLOW / TRANSFORM / HOLD / DENY
                |
                v
      Intel robot/controller
                |
                v
      outcome + receipt chain
```

This preserves the established OASSE separation already exercised in earlier builds: compute may derive evidence or validate a candidate, but **only Gatekeeper may authorize a consequential effect**.

## Why this placement

Tenki receives a SHA-256-bound artifact representing the exact `EvidenceFrame` and exact planner `ProposedAction`. The derive request contains only:

- `artifact_ref`
- `artifact_sha256`
- `requested_effect`
- `principal`

The response is accepted only when it explicitly remains non-authoritative and binds back to those exact values. A valid claim must contain:

- `authority: false`
- the exact `artifact_ref` and digest
- the exact requested effect
- the exact principal
- `compute_plane: "tenki"`
- `role: "derived_claim_only"`
- a 64-character hexadecimal `claim_hash`

The validated claim is attached under the reserved action metadata key:

```text
pre_authority_evidence.tenki
```

That enriched action is what Gatekeeper evaluates. The Tenki adapter cannot change `action_id`, actor, evidence binding, action type, target, speed, object, trajectory, or request time.

A planner is forbidden from pre-populating the reserved metadata key. That prevents a model or sponsor adapter from spoofing Tenki-derived evidence.

## Modes

`TENKI_MODE=off`

Default. No Tenki call occurs and the existing Physical AI behavior is unchanged.

`TENKI_MODE=observe`

A valid Tenki claim is attached and recorded. If Tenki is unavailable or its response is invalid, the failure is sealed as a `PRE_AUTHORITY_EVIDENCE` receipt and the existing Gatekeeper path continues without a Tenki claim. This is useful for initial onsite bring-up.

`TENKI_MODE=required`

A valid Tenki claim becomes a declared prerequisite for calling Gatekeeper. If Tenki is unavailable, malformed, incorrectly bound, too large, or attempts to assert authority, the pipeline produces HOLD and never calls the actuator. Tenki still does not grant authority; OASSE's local pipeline simply requires its evidence before requesting authority.

## Configuration

```sh
TENKI_MODE=observe
TENKI_DERIVE_URL=https://REPLACE_WITH_LIVE_TENKI_PREVIEW/derive
TENKI_TIMEOUT_S=0.20
# Optional only if the deployed /derive worker itself requires bearer auth.
TENKI_DERIVE_TOKEN=
```

Production/exposed endpoints require HTTPS. Loopback HTTP can be enabled explicitly for local testing with:

```sh
TENKI_ALLOW_LOOPBACK_HTTP=1
```

Do not send the Tenki platform API key to an arbitrary exposed worker endpoint. `TENKI_DERIVE_TOKEN` is intentionally separate from any Tenki CLI/platform credential.

## Onsite activation sequence

Do **not** make Tenki part of first robot bring-up. Keep `TENKI_MODE=off` until Intel camera, planner and controller contracts are identified.

Then:

1. Provision or restore the known Tenki `/derive` worker using the event-approved Tenki workflow.
2. Expose its worker port and obtain the HTTPS `/derive` URL.
3. Run the non-actuating contract probe:

   ```sh
   TENKI_DERIVE_URL=https://.../derive \
   python scripts/probe_tenki.py --output onsite/tenki-probe.json
   ```

4. Set `TENKI_MODE=observe` and run the software path. Verify a `PRE_AUTHORITY_EVIDENCE` receipt appears and the action reaching Gatekeeper contains the exact claim.
5. Measure total governed latency with Tenki enabled.
6. If the live worker is stable inside the evidence freshness budget, set `TENKI_MODE=required` for the judged proof.
7. If Tenki becomes unavailable during the event, return to `observe` or `off` only if the declared demo claim does not require Tenki. Never bypass Gatekeeper.

## Latency discipline

Tenki sits before authority, so its elapsed time consumes the same freshness budget as planning and Gatekeeper. The local dispatch guard still checks wall-clock and monotonic freshness after Gatekeeper and immediately before execution.

The default Tenki timeout is intentionally short: `0.20 s`. The previously observed OASSE Tenki `/derive` path completed on the order of tens of milliseconds, but **the current event run must be measured independently**. Do not reuse historical latency as an onsite claim.

If Tenki latency causes evidence to expire, the correct outcome is HOLD. Do not widen freshness limits simply to make the integration pass.

## Security boundary

The Tenki adapter:

- streams and bounds responses before JSON parsing;
- bounds the normalized claim size;
- requires exact artifact/effect/principal binding;
- rejects authority assertions anywhere in the returned claim;
- rejects claims that echo the configured derive credential;
- pools its HTTP client for low connection overhead;
- never receives Gatekeeper journal state;
- never receives robot-controller credentials from this integration;
- never dispatches hardware.

Tenki health and Gatekeeper health remain separate. A Tenki failure is a Tenki evidence-plane failure, not a Gatekeeper failure.

## TRANSFORM semantics

Tenki derives evidence about the **planner's exact proposed action**. Gatekeeper may still return `TRANSFORM`, for example by clamping speed. The transformed action is Gatekeeper-owned authority output and retains the original Tenki claim as evidence about the proposal that was evaluated.

Do not say Tenki authorized or independently approved the transformed action. The accurate statement is:

> Tenki derived non-authoritative evidence about the exact proposal; Gatekeeper used the complete bound request to determine the executable action.

## Proof surface

A strong live trace should show:

```text
OpenVINO inference
  -> EvidenceFrame ID/hash
  -> VLA ProposedAction ID
  -> Tenki artifact_ref + claim_hash (authority=false)
  -> Gatekeeper verdict + authorized action
  -> robot acknowledgement bound to action_id
  -> physical outcome
  -> PRE_AUTHORITY_EVIDENCE / AUTHORITY_DECISION / PHYSICAL_OUTCOME receipts
```

That demonstrates three separate roles without conflating them:

- **Intel** supplies Physical AI capability.
- **Tenki** supplies isolated derived compute/evidence.
- **Gatekeeper** supplies execution authority.
