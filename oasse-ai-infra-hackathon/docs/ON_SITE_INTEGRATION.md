# On-Site Intel Integration

The simulator already freezes the contracts that matter. `EvidenceFrame` is the only object the authority layer accepts as current sensor evidence. `ProposedAction` is the only object the planner can submit for authority. `AuthorityDecision` is the only path that can produce an `AuthorizedAction`. The SO-101 actuator adapter must refuse any raw planner action that has not crossed that boundary.

On site, replace `MockPerceptionProvider` with the event camera and OpenVINO/Anomalib path. Populate capture time from the actual frame, confidence from the detector, anomaly score/localization from the vision pipeline, and a hash or stable frame identifier from the captured evidence. Replace `MockVLAProvider` with the event VLA interface while preserving actor identity and the evidence reference used to create the proposal. Replace `SimulatedActuator` with the SO-101 control surface and expose only the authorized-action method.

The first physical rehearsal should use the stale-frame case because it isolates the research claim cleanly. Capture a clear workspace, delay beyond the configured evidence TTL, keep the planned action otherwise unchanged, and show that the robot does not move. Then capture a fresh equivalent frame and show ALLOW. The visual change is almost nothing; the authority state changes completely.

The next strongest case is TRANSFORM. Have the planner propose a motion above the authority ceiling. Gatekeeper should issue a constrained authorized action with the allowed speed rather than blindly pass or globally deny the task. The receipt must contain both original and authorized action forms.
