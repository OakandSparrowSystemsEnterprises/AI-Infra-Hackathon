# Sorting controller measurement

The recorded native sorting trace exposed a brief servo/grip transient: a command at the authorized ceiling could produce measured carrier velocity slightly above that ceiling. Command-value assertions alone did not detect this. The sorting controller now commands at most 85 percent of the authorized ceiling, and regression tests inspect measured velocity for both destinations at 0.20 and 0.35 meters per second.

The existing 500 ms evidence lease and authority speed ceilings are not loosened. Outcomes preserve the actual peak command, actual measured peak and the controller factor. If a physics disturbance drives measured velocity over the authorized ceiling, further stepping stops and the outcome is UNKNOWN with MEASURED_SPEED_EXCEEDED and possible partial effects. A regression injects that violation after one native step and verifies it cannot become success.

This is empirical validation for the declared Cartesian suction model, not a universal velocity guarantee or a physical robot safety certification. A measured violation cannot undo a physics step already taken. The onsite controller still requires independent limits, braking and operator-supervised validation.
