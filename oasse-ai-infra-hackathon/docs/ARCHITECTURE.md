# Architecture

The system is divided into a perception plane, planning plane, authority plane, execution plane, and evidence plane. Perception and planning may be probabilistic. The authority boundary is deterministic for a declared policy version. Execution is reachable only through an authorized action object. Evidence is sealed before the effect, and the physical outcome is chained afterward rather than retroactively changing the decision.

```text
Camera / Sensors
      |
      v
Perception / Anomalib / OpenVINO
      |  EvidenceFrame
      v
VLA / Physical AI Studio
      |  ProposedAction
      v
+----------------------------------+
| Gatekeeper Authority Boundary    |
| exact actor + evidence + action  |
| ALLOW / TRANSFORM / HOLD / DENY  |
+----------------------------------+
      | AuthorizedAction only
      v
Controlled Actuator / SO-101
      |
      v
Outcome observation -> chained receipts
```

In this repository the Gatekeeper authority boundary is the `AuthorityClient` interface in `src/oasse_physical_ai/gatekeeper_client.py`. By default it is filled by `ReferenceAuthorityEngine` (`src/oasse_physical_ai/policy.py`), an MIT-licensed local reference engine used for simulation, CI, and rehearsal. With `AUTHORITY_MODE=live` it is filled by `GatekeeperClient`, an MIT-licensed HTTP adapter that calls the proprietary Gatekeeper production service. That service is not contained in this repository. See `NOTICE.md`.

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

Perception supplies `e_n=P(x_n)`. A planner proposes `a_n`. Gatekeeper maps that proposal to an unchanged admissible action (**ALLOW**), an explicitly authorized admissible replacement (**TRANSFORM**), or no executable action under the current conditions (**HOLD/DENY**).

The architecture can therefore be read as:

```text
Observe -> Propose -> Project into the admissible state space -> Execute -> Prove
```

This is a conceptual model for the existing implementation, not a new runtime subsystem. See [Authority as an Invariant-Preserving Transition System](AUTHORITY_INVARIANT.md) for the complete formulation and claim boundaries.

## Capability is not authority

The critical invariant at the engineering level is `technical capability != execution authority`. Authentication can establish the actor. Perception can establish evidence. The VLA can propose motion. The actuator can be physically capable of motion. None of those conditions alone authorizes the state transition.

Freshness is treated as an authority property rather than a perception-only metric. If the environment changed after observation, the action can be technically valid relative to an old frame and still lack present authority. This is why the demo intentionally holds stale evidence instead of merely attaching a warning.

TRANSFORM is also an authority result rather than an unconstrained model rewrite. The reference policy only permits a bounded reduction of speed. The authorized action remains tied to the original action identity and the receipt records the transformation.

A detected defect illustrates the separation between facts and authority. Perception may report an anomaly, but that does not itself mean the action violates the authority invariant. A reject-route proposal can remain fully admissible and receive ALLOW.

## Constraint is not planning

The authority invariant constrains the transition set; it does not select the uniquely optimal action among all admissible actions. A VLA, planner, operator, or higher-level policy still chooses proposals. Authority determines whether the exact proposed transition belongs to the currently admissible set.

This prevents the governance layer from quietly becoming the planner and keeps the demo claim narrow: Gatekeeper governs execution; it does not claim to solve motion planning or optimal control.
