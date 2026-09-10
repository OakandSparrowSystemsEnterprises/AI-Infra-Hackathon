SCENARIOS = {
    "allow": "Fresh evidence, clear workspace, normal velocity -> ALLOW",
    "defect": "Fresh high anomaly evidence routes cube to reject bin -> ALLOW",
    "stale": "Evidence age exceeds authority TTL -> HOLD",
    "occupied": "Workspace occupancy invalidates motion authority -> DENY",
    "overspeed": "Proposed speed exceeds configured ceiling -> TRANSFORM",
    "identity_mismatch": "Unrecognized planner principal -> DENY",
    "binding_mismatch": "Action references different evidence identity -> DENY",
    "low_confidence": "Perception confidence below authority floor -> HOLD",
}
