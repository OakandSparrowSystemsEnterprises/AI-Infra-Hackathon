# Tomorrow Onsite: integration order

The repository side is ready for hardware integration. Do not begin by editing authority semantics. Tomorrow's job is to bind event-provided hardware and trained-model components into the tested seams, then collect evidence from the exact tested commit.

## Before touching the robot

1. Pull `main` and record `git rev-parse HEAD`. Keep the worktree clean.
2. Install the event-provided stack according to organizer instructions. Do not replace working event packages merely to match local versions.
3. Run the non-actuating machine preflight:

```sh
python scripts/onsite_preflight.py --output onsite/preflight.json --require-anomalib --require-lerobot
```

4. Identify the correct camera index, then explicitly test one frame:

```sh
python scripts/onsite_preflight.py --output onsite/preflight-camera.json --camera-index 0 --require-anomalib --require-lerobot
```

This opens and releases the selected camera. It does not invoke an actuator.
5. Configure `GATEKEEPER_URL` and `GATEKEEPER_TOKEN` locally. Never paste the token into an issue, chat transcript, receipt, screenshot, or committed file.
6. Run the existing non-actuating Gatekeeper contract probe using the expected deployed policy version. Save its JSON output.

## Integration order

Bind components in this order because each stage can be tested without granting the next stage physical effect:

**Camera first.** Replace the frame-source callback with the onsite camera. Record frame dimensions, timestamps, sequence behavior, and camera ID. Confirm the exact frame bytes are hashed before inference.

**Detector second.** Bind the trained Anomalib/OpenVINO export to the inference seam. Verify a normal object and a visibly marked object produce the expected normalized evidence. Perception still has no actuator access.

**Planner third.** Bind the trained VLA/LeRobot output to `VLAProvider`. Confirm every proposal contains explicit action type, object ID, destination, speed, and trajectory, and is bound to the exact evidence ID. Do not add defaults to make incomplete model output executable.

**Robot mapping fourth.** Implement the event robot adapter behind the `Actuator` seam. Keep the final send function behind the orchestrator's pre-send gate. First test serialization/mapping without motion when the hardware API supports a dry-run or command-inspection mode.

**Authority fifth.** Switch to production Gatekeeper only after the non-actuating contract probe passes. Confirm `/health` reports live authority and that a deliberate unavailable endpoint produces HOLD with no actuator call.

**Motion last.** With the hardware operator's approval, perform the smallest permitted movement before running the full sorting task. Record both the normal and defective sort. Then run stale-evidence and safe-interruption demonstrations under the event's hardware-safety procedures.

## Acceptance record

Copy `config/onsite-acceptance.example.json` outside the source tree or to an ignored local path. Fill it only from observed evidence. `verified_commit` must be the exact 40-character commit SHA used for the demonstration. `operator` must identify the person making the attestation. A field remains false until its corresponding event has actually been observed.

Validate it with:

```sh
python scripts/verify_onsite_acceptance.py onsite/acceptance.json --output onsite/acceptance-validation.json
```

This validator checks structure, exact commit binding, and whether all required fields are true. It does not certify physical safety.

## Required proof before submission

The final evidence set should contain the clean commit SHA, machine preflight, camera frame evidence, detector/model identity, Gatekeeper contract probe, authority mode, normal sort, defective sort, transformed/limited action, stale or unavailable authority no-motion proof, safe-interruption result, final post-action observation, receipt-chain verification, latency metrics, and the recorded demo video.

Do not call the build hardware-complete if any of those are still simulated. Keep simulation and hardware results labeled separately.

## Stop conditions

Stop integration and diagnose rather than bypassing a guard when evidence is stale, the frame identity changes unexpectedly, model output is incomplete, Gatekeeper cannot establish the expected contract, the robot adapter cannot intercept the final command before send, receipt verification fails, or the hardware operator has not approved motion.
