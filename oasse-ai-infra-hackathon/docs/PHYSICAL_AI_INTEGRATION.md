# Physical AI Integration Plan

The repository now separates four concerns behind explicit interfaces:

1. Perception produces `EvidenceFrame` facts.
2. A VLA produces a `ProposedAction` bound to that exact evidence.
3. Gatekeeper independently returns `ALLOW`, `TRANSFORM`, `HOLD`, or `DENY`.
4. An actuator receives only the authorized action after the execution gate.

The intended live path is:

`camera -> Intel/OpenVINO -> EvidenceFrame -> LeRobot/VLA -> ProposedAction -> Gatekeeper -> actuator -> receipt`

## Intel/OpenVINO lane

`OpenVINOPerceptionProvider` accepts an injected frame source and inference callable so local CI does not require event hardware or OpenVINO to be installed. The adapter owns the evidence contract:

- capture time is preserved exactly for freshness checks;
- the raw frame is SHA-256 hashed before authority evaluation;
- confidence, anomaly score, anomaly localization, pose, dimensions, camera identity, and frame sequence are first-class evidence fields;
- framework-specific scalars and arrays are normalized into plain JSON-safe Python values before they can cross the authority boundary.

Perception reports facts only. It never decides whether an action is permitted.

## LeRobot / MuJoCo lane

`LeRobotVLAProvider` accepts an injected policy callable and turns its output into a `ProposedAction`. The adapter always binds the proposal to the exact `EvidenceFrame.evidence_id`; it cannot grant authority.

`MuJoCoActuator` wraps a simulator execution callback. It is reachable only after the orchestrator receives an executable Gatekeeper decision.

The external `jeongeun980906/lerobot-mujoco-tutorial` repository is a workflow reference only. No source from that repository is vendored or copied into this project. The integration here is independently implemented against our own provider contracts.

## Demo proof sequence

The minimum compelling demo is:

1. A fresh camera frame is observed and hashed.
2. OpenVINO produces a normalized evidence object.
3. A VLA proposes a pick-and-place action bound to that evidence.
4. Gatekeeper evaluates the exact evidence/action pair.
5. `ALLOW` executes as proposed, `TRANSFORM` executes only the authorized replacement, and `HOLD`/`DENY` cause no actuator call.
6. The authority decision and physical outcome are sealed into the receipt chain.

The adversarial sequence should include stale evidence, low confidence, changed/reused frame evidence, an overspeed proposal, and an authority outage.

## Team seams

Jackson owns camera/perception integration through `PerceptionProvider` and `EvidenceFrame`.

The simulation/VLA lane owns LeRobot or another VLA through `VLAProvider`, plus MuJoCo through the actuator seam.

Gatekeeper semantics, receipt sealing, and the final execution gate remain independent of both lanes.
