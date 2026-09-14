# Tomorrow Onsite: integration order

The repository side is ready for hardware integration. Do not begin by editing authority semantics. Tomorrow's job is to bind event-provided hardware and trained-model components into the tested seams, then collect evidence from the exact tested commit.

For the first-hour door plan and organizer schedule, read [`ONSITE_ENTRY_PLAN.md`](ONSITE_ENTRY_PLAN.md). For sponsor SDK wiring, read [`ONSITE_SPONSOR_BINDING.md`](ONSITE_SPONSOR_BINDING.md).

## Arrival priority

Conference registration opens at **7:30 AM**. Target arrival is **7:45-8:00 AM**. Hackathon Rooms **203/204** open at **9:00 AM**, when Intel hardware distribution and coordination begin.

The first integration objective is not motion. It is:

**Intel verifier green -> sponsor bindings resolved -> camera -> detector -> planner -> Gatekeeper probe -> robot serializer/dry-run -> smallest approved motion.**

Do not switch tracks, rewrite the architecture, or spend the first hour on general Summit networking.

## Before touching the robot

1. Pull `main` and record `git rev-parse HEAD`. Keep the worktree clean.
2. Use the event-provided Intel environment as delivered. Do not replace working event packages merely to match local versions.
3. Run Intel's own non-actuating stack verifier first:

```sh
conda activate intel_dev_env
python verify_stack.py
```

4. Run our non-actuating machine preflight:

```sh
python scripts/onsite_preflight.py --output onsite/preflight.json --require-anomalib --require-lerobot
```

5. Identify the correct camera index, then explicitly test one frame:

```sh
python scripts/onsite_preflight.py --output onsite/preflight-camera.json --camera-index 0 --require-anomalib --require-lerobot
```

This opens and releases the selected camera. It does not invoke an actuator.

6. Ask the Intel engineer for the exact camera, detector, planner, robot-send, acknowledgement, coordinate-frame, speed-limit and stop/cancel contracts listed in `ONSITE_SPONSOR_BINDING.md`.
7. Scaffold the ignored local bridge:

```sh
python scripts/scaffold_onsite_bridge.py --output-dir onsite
```

8. Fill the local bridge functions and resolve the sponsor bindings without invoking them:

```sh
PYTHONPATH=onsite:$PYTHONPATH \
python scripts/validate_sponsor_bindings.py onsite/bindings.json \
  --output onsite/binding-validation.json
```

9. Configure `GATEKEEPER_URL` and `GATEKEEPER_TOKEN` locally. Never paste the token into an issue, chat transcript, receipt, screenshot, or committed file.
10. Run the existing non-actuating Gatekeeper contract probe using the expected deployed policy version. Save its JSON output.

## Integration order

Bind components in this order because each stage can be tested without granting the next stage physical effect:

**Camera first.** Use `SponsorRGBSource` or `OpenCVRGBSource` around the onsite camera. Record frame dimensions, timestamps, sequence behavior, camera ID, and the source of workspace/geometry context. Confirm the exact frame bytes are hashed before inference.

**Detector second.** Bind the trained Anomalib/OpenVINO export to `NativeOpenVINOPerception` + `AnomalibDecoder`. Verify a normal object and a visibly marked object produce the expected normalized evidence. Perception still has no actuator access.

**Planner third.** Bind Physical AI Studio / VLA / LeRobot output to `SponsorVLAProvider` or `LeRobotVLAProvider`. Confirm every proposal contains explicit action type, object ID, destination, speed, and trajectory, and is bound to the exact evidence ID. Do not add defaults to make incomplete model output executable.

**Robot mapping fourth.** Bind the event robot/controller behind `SponsorActuator` or `SponsorGuardedActuator`. Keep the final send function behind the orchestrator's pre-send gate. First test serialization/mapping without motion when the hardware API supports a dry-run or command-inspection mode. A successful acknowledgement must correlate to the exact action ID.

**Authority fifth.** Switch to production Gatekeeper only after the non-actuating contract probe passes. Confirm `/health` reports live authority and that a deliberate unavailable endpoint produces HOLD with no actuator call.

**Motion last.** With the hardware operator's approval, perform the smallest permitted movement before running the full sorting task. Record both the normal and defective sort. Then run stale-evidence and safe-interruption demonstrations under the event's hardware-safety procedures.

## Information windows not to miss

On Tuesday, stop integration for:

- **10:30 AM** opening ceremony
- **10:45 AM** partners' words
- **11:10 AM** project submission workshop + pitching-form explanation

Those are the moments most likely to contain challenge-specific sponsor instructions or submission requirements. Capture them before resuming the build.

The event-specific workshop is authoritative if it differs from LabLab's general submission guide. Confirm repository visibility, demo URL requirement, video duration/format, deck format, sponsor-technology fields, track selection, and any required evidence.

## Acceptance record

Copy `config/onsite-acceptance.example.json` outside the source tree or to an ignored local path. Fill it only from observed evidence. `verified_commit` must be the exact 40-character commit SHA used for the demonstration. `operator` must identify the person making the attestation. A field remains false until its corresponding event has actually been observed.

Validate it with:

```sh
python scripts/verify_onsite_acceptance.py onsite/acceptance.json --output onsite/acceptance-validation.json
```

This validator checks structure, exact commit binding, and whether all required fields are true. It does not certify physical safety.

## Required proof before submission

The final evidence set should contain the clean commit SHA, Intel stack verification, machine preflight, sponsor-binding validation, camera frame evidence, detector/model identity, Gatekeeper contract probe, authority mode, normal sort, defective sort, transformed/limited action, stale or unavailable authority no-motion proof, safe-interruption result, final post-action observation, receipt-chain verification, latency metrics, and the recorded demo video.

Do not call the build hardware-complete if any of those are still simulated. Keep simulation and hardware results labeled separately.

## Stop conditions

Stop integration and diagnose rather than bypassing a guard when evidence is stale, the frame identity changes unexpectedly, model output is incomplete, Gatekeeper cannot establish the expected contract, the robot adapter cannot intercept the final command before send, the controller cannot correlate success to the command, receipt verification fails, the stop/E-stop path is unknown, or the hardware operator has not approved motion.
