# Phase 2: guarded native simulation

The new runnable path is simulator state observation, an explicit scripted Cartesian proposal, reference authority evaluation, replay/freshness/scene dispatch checks, native MuJoCo control and physics steps, and a chained outcome receipt. This is a real MuJoCo dynamics harness, not a callback pretending to advance a simulator.

It is deliberately a three-axis Cartesian carrier scene authored in this repository. It is not an SO-101 model, a bimanual competition environment, or a grasping-success demonstration. The scripted baseline is not a trained LeRobot/VLA model. Simulator ground truth is labeled `mujoco-state-ground-truth`, not camera/OpenVINO perception. `grasping_tested` is false in every native runtime outcome. The next integration substitutes the event robot model, observation stream and trained policy without relocating authority into them.

## Run

From `oasse-ai-infra-hackathon`, run:

```sh
python -m pip install -e ".[dev,simulator]"
python -m pytest tests -q
python scripts/run_demo.py
python scripts/run_mujoco_demo.py --output mujoco-smoke.json
```

MuJoCo remains optional for the default API and Docker image. The simulator CI job explicitly imports MuJoCo before running tests, so a missing dependency cannot silently skip its runtime validation.

## Evidence and action contract

Perception must explicitly report `confidence`, `workspace_clear` and `anomaly_score`. Missing workspace information is not a clear workspace. The policy must explicitly report `action_type`, `object_id`, `target_bin`, `speed_mps` and `trajectory`. Missing policy output does not synthesize a movement. The existing mock scenario factories remain available only as declared demonstration fixtures.

NumPy arrays and scalars are copied into plain JSON values. Array `tolist()` is used before scalar `item()`. Normalization rejects nonfinite values, cycles, unsupported objects, excessive nesting and oversized object graphs. Capture bytes are copied before inference, and the content hash is computed from those exact bytes. Timestamps and sequence numbers are nonnegative integers. Bounding boxes use normalized ordered XYXY values, pose is XYZ meters plus roll/pitch/yaw radians, and dimensions are positive XYZ meters. These validations do not calibrate a camera or prove the truth of an inference.

## Local dispatch checks

DispatchGuard can remove permission but cannot grant it. Evidence and proposal fingerprints are recorded before the authority call; mutation or substitution is rejected. Freshness is checked after the authority returns and again after sealing the decision, immediately before dispatch. Future timestamps are rejected. The reference authority itself also rejects future timestamps rather than treating them as age zero.

Consumed evidence and action identities cannot be reused within a 4096-dispatch rolling window. Camera sequence high-water marks prevent reuse or rollback during the orchestrator's lifetime. Identical pixels in a new capture with a new identity and increasing sequence are allowed: a stationary scene is not automatically a replay. These checks do not authenticate camera identities or detect a malicious source inventing new timestamps/sequences. Replay state is in memory and is not durable across process restarts. Create a new orchestrator for a new simulation/camera session whose sequence restarts. Capacity is bounded to 64 camera streams per orchestrator.

When a scene-hash callback is wired, the independently sampled current scene must match the observed `EvidenceFrame.scene_hash` at launch. The native demo wires this callback to simulator state. Generic camera adapters do not thereby acquire scene-change detection automatically. This is a single-process orchestration control, not an operating-system access-control boundary against code with direct access to the actuator.

The native runtime checks evidence freshness before every physics step. It freezes the simulation on interruption and records an unknown/partial outcome after any steps have already happened. A physical robot cannot freeze time; robot braking, collision avoidance, control-loop timing and hardware emergency stops require separate integration and validation. Scene comparison is at dispatch, not a continuous collision monitor. The input action's speed caps velocity commands; test results also inspect measured simulated velocity for the declared simple scene. This is not a general hardware velocity guarantee.

## Execution reporting

`dispatch_attempted` means the actuator was invoked. `executed` is true only for an explicit `EXECUTED` result. Missing or unrecognized status, callback errors, and malformed results become `UNKNOWN`, never invented success. Every attempted dispatch receives an outcome receipt including partial/unknown outcomes. A failed dispatch is not automatically retried with the same evidence. A blocked command has no actuator call and no physics steps.

Pipeline errors produce a clearly marked `pipeline-local-failure-v1` HOLD with an error observation placeholder, never fabricated valid perception. No raw exception messages, credentials or arbitrary invalid objects are copied into these receipts.

The original authority API and proprietary Gatekeeper implementation are not replaced. This repository still supplies the MIT-licensed reference engine and the HTTP boundary only. Tests of mock service responses are not proof of production endpoint connectivity.

## Reproduction scope

The native demo asserts fresh ALLOW and clamped TRANSFORM move the simulated carrier. Stale, future, occupied, low-confidence and changed-scene cases perform zero physics steps. Replayed evidence adds zero steps after the first valid dispatch. Separate tests interrupt a trajectory after three real physics steps and verify an UNKNOWN outcome with possible partial effects.

Implementation references: MuJoCo's official Python bindings and XML reference, and NumPy's official `ndarray.tolist`/`ndarray.item` documentation. No source or assets from the external LeRobot tutorial are included.
