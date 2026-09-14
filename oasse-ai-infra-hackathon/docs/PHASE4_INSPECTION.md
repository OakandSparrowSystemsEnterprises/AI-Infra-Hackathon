# Phase 4: inspection task and submission rehearsal

The new task path inspects rendered RGB through the existing native OpenVINO runner, selects an explicit sorting recipe, obtains an independent authority decision, transports a free cube through MuJoCo dynamics, releases it, and takes a new post-execution state observation. Task completion requires the object to be in the authorized destination, released and settled. An actuator ACK or an executed trajectory alone cannot complete the task.

The simulator is an authored Cartesian suction model. An idealized weld attaches a free cube after the carrier reaches its grip point. Gravity, transport and release then use native physics steps. There is no teleporting the object to its destination. A direct object-position change exists only for the named scene-disturbance test. This is not an SO-101 model, finger-contact grasp proof, or physical braking model. The detector remains the reference-image difference graph and the planner remains a scripted seven-waypoint recipe.

## Run the complete rehearsal

Use the app directory `oasse-ai-infra-hackathon`. On a separate development machine, install `.[dev,simulator,perception]` into a virtual environment. On an organizer-provided machine, preserve the supported Intel environment and first use `python scripts/check_environment.py --native`; do not replace its PyTorch or OpenVINO stack automatically. Headless Linux rendering requires a working MuJoCo OpenGL backend, such as `MUJOCO_GL=osmesa` with libosmesa6 installed.

```sh
python scripts/rehearse_submission.py --profile native --output /tmp/oasse-rehearsal
python scripts/verify_evidence.py /tmp/oasse-rehearsal/inspection
```

The output directory must be new or empty and outside the source tree. The command runs the full tests, the original reference demo, native motion demo, native vision demo and task-level sorting rehearsal. It preserves JUnit results, command logs, installed versions, source commit, readiness report and the inspection bundle. A native rehearsal with skipped tests is not marked passed. No package installation, robot command or online submission is performed by the rehearsal tool. The reference profile is useful without native dependencies but does not satisfy native rehearsal readiness.

For only the inspection demonstration, run `python scripts/run_inspection_demo.py --bundle /tmp/oasse-inspection --zip /tmp/oasse-inspection.zip`. Open its `index.html` locally to show original captured images alongside decisions, task outcomes and receipt references. This is an offline evidence viewer, not a live robot-control dashboard.

## Cases and acceptance

Normal and visibly marked cubes must be released in the accept and reject destinations respectively. The overspeed proposal must use the authorized replacement speed. Stale or future evidence, an occupied workspace, a changed scene and the mocked authority outage must produce zero physics steps. Replayed evidence must add zero steps. Mid-motion lease expiration and an obstruction must stop further stepping and report an unknown outcome with possible partial effects. A failed postcondition must not be reported as a completed task, even after the actuator reports execution.

`InspectionTask.run()` is one-shot and idempotent within the process. Repeated calls return a detached recorded result. An interrupted task cannot automatically retry even when its last receipt could not be written. Its task receipt links the preceding decision and outcome and preserves the new verification observation. This is in-memory task deduplication, not restart-safe physical exactly-once execution.

The existing 500 ms evidence lease remains unchanged. Simulation advances faster than wall time; simulated task duration and wall-clock freshness are different measurements. The software freezes the simulation on interruption. A real controller needs its own safe stop and continuous observations; this simulated behavior must not be represented as hardware braking validation.

## Camera and trained-detector handoff

`OpenCVRGBSource` is an optional driver for an explicitly selected local camera. It snapshots BGR frames into RGB8, rejects undeclared resolution/format changes, and requires fresh `CameraContext` from the operator's actual context source. It does not infer workspace clearance or generate calibration geometry. The host timestamp bounds acquisition, not the unobservable camera exposure or internal buffering. A slow read is rejected after it returns; the driver does not claim to interrupt a blocked operating-system camera call.

`AnomalibDecoder` accepts explicit `pred_score` and `anomaly_map` output names, image/pixel thresholds, a calibration identifier and a declared confidence. Raw anomaly scores are preserved as such, not called probabilities. The normalized evidence score encodes a thresholded normal/defect decision as zero or one. An exported model must match the native runner's exact static NCHW float32 RGB divided-by-255 input, or use an explicitly reviewed preprocessing adapter. No trained weights or calibrated thresholds are invented here.

## Proof boundary

The evidence bundle includes a file-hash manifest, source commit, complete receipt chains, model artifacts and unedited rendered RGB captures encoded as PNG. `verify_evidence.py` verifies content hashes and receipt/task links without running a model or making a network call. Keep the expected manifest SHA-256 separately to detect wholesale replacement. The manifest and hash chains are unsigned integrity records, not proof of a particular signer's identity or of a real camera event. Public claims must match the declared simulation, detector, planner and authority modes.
