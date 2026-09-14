# Onsite Sponsor Binding Kit

This repository is designed so event-provided SDKs, models, cameras, planners, and robot controllers can be attached **without editing the authority core**.

The rule onsite is:

> **Adapt sponsor capability into the tested seams. Do not adapt Gatekeeper to the sponsor.**

The authority path remains:

`camera/context -> perception -> EvidenceFrame -> planner/VLA -> ProposedAction -> Gatekeeper -> dispatch gate -> actuator -> observed outcome -> receipts`

## Intel kit we expect onsite

Organizer and Intel materials say the onsite Intel equipment is preloaded around the Intel Physical AI stack:

- Ubuntu 24.04 LTS
- Intel Core Ultra / Arc graphics and NPU stack
- `intel_dev_env`
- Physical AI Studio
- OpenVINO 2026.3
- Anomalib 2.6.0
- LeRobot with PyTorch XPU
- Intel's `verify_stack.py`

Use Intel's verifier first. Do not reinstall or repin a working event machine just to make it resemble the local development environment.

Official Intel resource:
https://docs.openedgeplatform.intel.com/dev/edge-ai-suites/robotics-ai-suite/resources/hackathon_resources.html

## Six sponsor seams

The code already has a stable boundary for each thing an onsite sponsor engineer is likely to hand us.

| Sponsor gives us | Bind it to | What must cross the seam |
| --- | --- | --- |
| Camera SDK / frame callback | `SponsorRGBSource` or `OpenCVRGBSource` | RGB8 bytes, capture time, sequence, camera ID, explicit workspace/context source |
| Detector / Anomalib export | `NativeOpenVINOPerception` + `AnomalibDecoder` | score/map outputs under an explicit calibration contract |
| Physical AI Studio / VLA / LeRobot planner | `SponsorVLAProvider` or `LeRobotVLAProvider` | action type, object, target, speed, trajectory |
| Robot SDK / ROS2 / controller API | `SponsorActuator` | exact authorized command only; explicit status + exact action ID acknowledgement |
| Controller with continuous validity callback | `SponsorGuardedActuator` | same command plus `still_authorized()` |
| Stop / brake / E-stop | lower controller or `SponsorGuardedActuator` integration | actual stop behavior must be observed onsite, never inferred |

Transport details stay **inside the callback**. If Intel gives us a Python API, ROS2 service, REST endpoint, local socket, controller object, or Physical AI Studio inference object, only the thin callback changes. The orchestrator, Gatekeeper client, replay guard, receipts, and policy semantics do not.

## Physical AI Studio fast path

The public Physical AI Studio project exposes Python, CLI and GUI workflows and can export policies to OpenVINO, ONNX or Torch. Its documented deployment loop uses an inference model with a `select_action(observation)` style call. That maps cleanly to our planner seam:

```python
# local/ignored onsite_bridge.py

def plan(evidence):
    observation = build_sponsor_observation(evidence)
    raw_action = policy.select_action(observation)
    return translate_sponsor_action(raw_action, evidence)
```

The translator is the only place sponsor-specific tensor shapes, joint order, coordinate frames and units should live. Its return value must satisfy the repository's explicit `ProposedAction` contract. Do not pass raw model tensors directly into Gatekeeper or the robot.

Physical AI Studio is currently a public-preview project and its APIs/workflows may change. **Onsite Intel mentor instructions are authoritative for the exact invocation.** The bridge exists so such a change costs one callback, not an architecture rewrite.

## Fast binding workflow

1. **Run Intel's own stack verifier.**

   ```sh
   conda activate intel_dev_env
   python verify_stack.py
   ```

   The healthy target is CPU/GPU/NPU visible to OpenVINO, XPU-backed PyTorch available, Anomalib and LeRobot importable, and Physical AI Studio present.

2. **Ask the Intel engineer for the six concrete contracts before writing code.**

   - Camera device/API and exact RGB format.
   - Detector artifact/export format and output tensor names.
   - Anomalib image/pixel thresholds or calibration profile.
   - Planner/VLA invocation and its coordinate-frame convention.
   - Final robot send API, units, home pose, speed limits, and acknowledgement format.
   - Stop/cancel/E-stop mechanism and whether it can interrupt a command already in flight.

3. **Create only a thin local bridge module.**

   ```sh
   python scripts/scaffold_onsite_bridge.py --output-dir onsite
   ```

   Then replace only the sponsor SDK calls in `onsite/onsite_bridge.py`. The directory is ignored by Git so tokens, local paths, and event-only glue are not accidentally committed.

4. **Resolve every software binding without actuating hardware.**

   ```sh
   PYTHONPATH=onsite:$PYTHONPATH \
   python scripts/validate_sponsor_bindings.py onsite/bindings.json \
     --output onsite/binding-validation.json
   ```

   The validator imports the configured functions but does not call the camera, model, planner, or actuator.

5. **Prove each lane independently before enabling the next one.**

   Camera -> detector -> planner -> Gatekeeper probe -> robot serializer/dry-run -> smallest approved motion.

6. **Do not edit these files to accommodate sponsor SDK quirks unless a real contract defect is proven:**

   - `orchestrator.py`
   - `dispatch.py`
   - `receipts.py`
   - `gatekeeper_client.py`
   - authority verdict semantics

   Sponsor-specific field names belong in the bridge. Coordinate conversion belongs in the bridge. SDK initialization belongs in the bridge.

## Normalized contracts

### Camera

`SponsorRGBSource` accepts either an `RGBFrame` or a mapping with:

- `data`: exact raw RGB8 bytes, or `rgb`: uint8 HxWx3 array
- `captured_at_ms`
- `workspace_clear`
- `context_source`
- optional `camera_id`, `sequence`, `scene_hash`
- optional object pose/dimensions

No safety fact is defaulted.

### Planner

`SponsorVLAProvider` requires:

- `action_type`
- `object_id`
- `target_bin`
- `speed_mps`
- `trajectory`

If the sponsor planner supplies an `evidence_id`, it must match the exact observed evidence. Missing motion fields are not invented.

### Actuator

`SponsorActuator` sends this canonical command:

- `action_id`
- `actor_id`
- `action_type`
- `object_id`
- `target_bin`
- `speed_mps`
- `trajectory`
- `evidence_id`
- `requested_at_ms`

A sponsor acknowledgement must provide an explicit status and command/action identifier. Vendor status strings can be mapped to `EXECUTED`, `NOT_EXECUTED`, `FAILED`, or `UNKNOWN`. An `EXECUTED` acknowledgement for a different action ID is rejected.

## Onsite stop conditions

Do not route around the authority boundary if any sponsor component:

- cannot expose the final command before send;
- silently fills missing action fields;
- changes units or coordinate frames without an explicit transform;
- cannot identify the camera/frame source;
- cannot provide a bounded model output contract;
- reports success without a command-correlated acknowledgement;
- bypasses the stop/E-stop procedure required by the hardware operator.

If one of those occurs, fix the thin bridge or reduce demo scope. Do not weaken the core.
