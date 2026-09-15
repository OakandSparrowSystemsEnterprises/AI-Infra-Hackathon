# Architecture

> For a principal-engineer review of trust boundaries, temporal semantics, failure behavior, data contracts, replay handling and residual risks, start with **[Senior Engineer Architecture Review](SENIOR_ENGINEER_ARCHITECTURE.md)**. The optional Tenki evidence plane is specified separately in **[Tenki Integration](TENKI_INTEGRATION.md)**.

The system is divided into a perception plane, planning plane, optional derived-compute plane, authority plane, execution plane, and evidence plane. Perception and planning may be probabilistic. Derived compute may add evidence but cannot authorize. The authority boundary is deterministic for a declared policy version. Execution is reachable only through an authorized action object. Evidence is sealed before the effect, and the physical outcome is chained afterward rather than retroactively changing the decision.

```text
**INTEL PHYSICAL AI CAPABILITY PLANE**
Camera / Sensors
      |
      v
OpenVINO / Anomalib
      |  EvidenceFrame
      v
VLA / Physical AI Studio
      |  ProposedAction
      v
+----------------------------------+
| Tenki Derived Evidence (optional)|
| exact artifact hash + principal  |
| authority = false                |
+----------------------------------+
      | same action + bound claim
      v
+----------------------------------+
| Gatekeeper Authority Boundary    |
| exact actor + evidence + action  |
| ALLOW / TRANSFORM / HOLD / DENY  |
+----------------------------------+
      | AuthorizedAction only
      v
Robotics AI Suite / Controlled Actuator
      |
      v
Outcome observation -> chained receipts
```

In this repository the Gatekeeper authority boundary is the `AuthorityClient` interface in `src/oasse_physical_ai/gatekeeper_client.py`. By default it is filled by `ReferenceAuthorityEngine` (`src/oasse_physical_ai/policy.py`), an MIT-licensed local reference engine used for simulation, CI, and rehearsal. With `AUTHORITY_MODE=live` it is filled by `GatekeeperClient`, an MIT-licensed HTTP adapter that calls the proprietary Gatekeeper production service. That service is not contained in this repository. See `NOTICE.md`.

The optional Tenki boundary is implemented in `src/oasse_physical_ai/tenki.py`. It hashes a normalized copy of the exact evidence/action artifact, invokes the external Tenki `/derive` worker, validates the returned non-authoritative claim, and attaches the claim only as reserved metadata before Gatekeeper evaluation. `TENKI_MODE=off` leaves the original execution path unchanged.

## Authority as an admissible state space

The deeper architecture is that authority does not merely attach a rule to a proposed action. It defines which state transitions count as executable.

Let `I` be the authoritative invariant and `\iota` the value that must survive execution:

$$
I(x_{n+1})=I(x_n)=\iota.
$$

Define

$$
X_I=\{x\in X:I(x)=\iota\}.
$$

Then an admissible controlled transition satisfies

$$
C_I:X_I\rightarrow X_I.
$$

Perception supplies `e_n=P(x_n)`. A planner proposes `a_n`. Optional Tenki compute may derive a non-authoritative claim `d_n=D(e_n,a_n)` bound to the exact proposal. Gatekeeper then maps the proposal, together with all declared evidence, to an unchanged admissible action (**ALLOW**), an explicitly authorized admissible replacement (**TRANSFORM**), or no executable action under the current conditions (**HOLD/DENY**).

The architecture can therefore be read as:

```text
Observe -> Propose -> Derive evidence (optional) -> Project into the admissible state space -> Execute -> Prove
```

This is a conceptual model for the existing implementation, not a claim that Tenki or Gatekeeper chooses the optimal action. See [Authority as an Invariant-Preserving Transition System](AUTHORITY_INVARIANT.md) for the complete formulation and claim boundaries.

## Capability is not authority

The critical invariant at the engineering level is `technical capability != execution authority`. Authentication can establish the actor. Perception can establish evidence. The VLA can propose motion. Tenki can derive evidence about that proposal. The actuator can be physically capable of motion. None of those conditions alone authorizes the state transition.

Freshness is treated as an authority property rather than a perception-only metric. If the environment changed after observation, the action can be technically valid relative to an old frame and still lack present authority. This is why the demo intentionally holds stale evidence instead of merely attaching a warning.

TRANSFORM is also an authority result rather than an unconstrained model rewrite. The reference policy only permits a bounded reduction of speed. The authorized action remains tied to the original action identity and the receipt records the transformation.

A detected defect illustrates the separation between facts and authority. Perception may report an anomaly, but that does not itself mean the action violates the authority invariant. A reject-route proposal can remain fully admissible and receive ALLOW.

## Derived compute is not authority

Tenki is intentionally placed outside the authority plane. Its accepted claim must say `authority=false`, `compute_plane=tenki`, and `role=derived_claim_only`. It cannot return an authorized action, verdict, permit, capability token, or other authority-bearing value through this contract.

The planner cannot forge the trusted Tenki slot because `pre_authority_evidence` is reserved by the orchestrator. The Tenki client independently computes the artifact digest from detached snapshots. A claim is rejected if its artifact reference, digest, requested effect, principal or claim-hash shape does not match the local request.

When Tenki is configured as `observe`, its failure is recorded but does not replace the existing Gatekeeper path. When configured as `required`, failure to obtain valid declared evidence produces a local HOLD before Gatekeeper; this is an OASSE pipeline requirement, not authority granted to Tenki.

For a Gatekeeper `TRANSFORM`, the Tenki claim remains evidence about the exact original proposal. Gatekeeper owns the authorized replacement. The system does not claim that Tenki independently approved the transformed action.

## Constraint is not planning

The authority invariant constrains the transition set; it does not select the uniquely optimal action among all admissible actions. A VLA, planner, operator, or higher-level policy still chooses proposals. Authority determines whether the exact proposed transition belongs to the currently admissible set.

This prevents the governance layer from quietly becoming the planner and keeps the demo claim narrow: Gatekeeper governs execution; it does not claim to solve motion planning or optimal control.
