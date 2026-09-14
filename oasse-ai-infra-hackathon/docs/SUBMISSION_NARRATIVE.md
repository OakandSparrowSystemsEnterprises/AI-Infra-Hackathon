# Submission narrative and demonstration script

## Description

Gatekeeper adds an independent pre-execution authority boundary to a physical-AI pipeline. Perception reports evidence, a planner proposes an action, and an authority decision permits, transforms, holds or denies the proposed effect. The integration binds evidence and action snapshots, refuses stale or replayed observations, and records both execution and separately observed task completion.

The current reproducible software demonstration uses rendered MuJoCo images, native OpenVINO inference, a scripted Cartesian sorting recipe and the repository's explicitly labeled reference authority engine. An idealized suction constraint transports and releases the simulated cube. Physical-camera, trained Anomalib/VLA and onsite arm integration must be described as completed only after those runs have been recorded. Production Gatekeeper is a separate service behind the API boundary and is not included in the MIT repository.

## Short pitch

A model can know what to do, and a robot can be capable of doing it, without having permission to do it now. We separate those questions. Intel's inference stack supplies the observations and proposed action. Gatekeeper independently evaluates whether that exact action is authorized using that evidence at that time. When an observation is stale or authority is unavailable, the action does not start. When authority changes the action, the original proposal cannot slip through. The receipt chain links what was observed, what was authorized, what was dispatched and what was independently verified afterward.

## Recorded demonstration

Start by showing the effective runtime and authority modes. Show a normal object, its inspection result, the proposed accept destination and the newly observed completed placement. Repeat with a defective object and the reject destination. Show an overspeed proposal next to its authorized replacement. Then demonstrate stale evidence or an authority outage: the planner can still propose, but no new movement is dispatched. Finish with the linked decision, outcome and task-verification records.

In the software rehearsal, use `inspection/index.html` as an offline fallback for the original images and execution records. It is saved evidence, not a live camera. Describe the suction grip as idealized and the policy/detector as reference components. During an onsite recording, replace those qualifications only with claims supported by the actual hardware trace.

## Measurements and claims

Report actual test count and failures from the frozen run's JUnit file. Separate authority evaluation time, client elapsed time, native inference time, simulated physics steps and measured task completion. Do not use a pure simulation wall-clock duration as a robot cycle-time claim. Preserve unknown or partial outcomes instead of converting them into successes.

The submission package must contain the tested commit, runnable instructions, original evidence, proof-scope statement and video/access fields. The bundle verifier checks hashes and semantic receipt links. It does not certify hardware safety, legal compliance, model accuracy or service identity. There is no automatic submission function.
