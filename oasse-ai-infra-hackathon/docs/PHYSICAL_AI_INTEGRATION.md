# Physical AI Integration Plan

The repository separates four concerns behind explicit interfaces:

1. Perception produces `EvidenceFrame` facts.
2. A VLA produces a `ProposedAction` bound to that exact evidence.
3. Gatekeeper independently returns `ALLOW`, `TRANSFORM`, `HOLD`, or `DENY`.
4. An actuator receives only the authorized action after the execution gate.

The intended live path is:

`camera -> Intel/OpenVINO -> EvidenceFrame -> LeRobot/VLA -> ProposedAction -> Gatekeeper -> actuator -> receipt`

## Intel/OpenVINO lane

`OpenVINOPerceptionProvider` accepts an injected frame source and inference callable. The adapter owns the evidence contract: capture time, content hash, confidence, anomaly score/localization, pose, dimensions, camera identity, and sequence are normalized into JSON-safe values before they cross the authority boundary.

Perception reports facts only. It never decides whether an action is permitted.

## LeRobot / MuJoCo lane

`LeRobotVLAProvider` accepts an injected policy callable and converts its output into a `ProposedAction` bound to the exact evidence identity. It cannot grant authority.

`MuJoCoActuator` and the native MuJoCo runtime are independently authored project code. The actuator boundary is reachable only after an executable authority decision.

No external tutorial source, assets, notebooks, model weights, or simulator implementation are copied into this repository. External runtimes are consumed through their installed packages or public APIs. See [`../../GREENFIELD.md`](../../GREENFIELD.md) for the repository provenance policy.

## Demo proof sequence

1. Observe and hash a fresh frame.
2. Normalize perception evidence.
3. Produce an evidence-bound proposal.
4. Evaluate the exact evidence/action pair at the independent authority boundary.
5. Execute only ALLOW or the explicit authorized TRANSFORM replacement; HOLD and DENY do not dispatch.
6. Seal the authority decision and any physical outcome into the receipt chain.

Adversarial cases include stale evidence, low confidence, changed/reused evidence, overspeed, and authority unavailability.

## Team seams

Camera/perception integration owns only the `PerceptionProvider` and `EvidenceFrame` side of the seam. VLA/simulation integration owns `VLAProvider` and actuator adapters. Gatekeeper semantics, receipt sealing, and the final execution gate remain independent of both lanes.
