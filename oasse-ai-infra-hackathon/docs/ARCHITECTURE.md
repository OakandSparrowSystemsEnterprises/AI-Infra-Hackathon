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
Outcome Receipt -> chained to decision receipt
```

In this repository the Gatekeeper authority boundary is the `AuthorityClient` interface in `src/oasse_physical_ai/gatekeeper_client.py`. By default it is filled by `ReferenceAuthorityEngine` (`src/oasse_physical_ai/policy.py`), an MIT-licensed local reference engine used for simulation, CI, and rehearsal. With `AUTHORITY_MODE=live` it is filled by `GatekeeperClient`, an MIT-licensed HTTP adapter that calls the proprietary Gatekeeper production service. That service is not contained in this repository. See `NOTICE.md`.

The critical invariant is `technical capability != execution authority`. Authentication can establish the actor. Perception can establish evidence. The VLA can propose motion. The actuator can be physically capable of motion. None of those conditions alone authorizes the state transition.

Freshness is treated as an authority property rather than a perception-only metric. If the environment changed after observation, the action can be technically valid relative to an old frame and still lack present authority. This is why the demo intentionally holds stale evidence instead of merely attaching a warning.

TRANSFORM is also an authority result rather than an unconstrained model rewrite. The reference policy only permits a bounded reduction of speed. The authorized action remains tied to the original action identity and the receipt records the transformation.
