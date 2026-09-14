# Phase 3: native image inference and hardened dispatch

The runnable integration now renders actual RGB pixels with MuJoCo, executes a compiled OpenVINO IR graph on an explicitly selected CPU, normalizes image-derived anomaly evidence, evaluates a scripted proposal through the independent authority boundary, and dispatches into native MuJoCo dynamics only when permitted. The default HTTP service remains the lightweight reference demo; the native path has its own executable smoke runner.

## Reproduce

Use Python 3.11 or later from the application directory `oasse-ai-infra-hackathon`. On headless Ubuntu, install `libosmesa6` through the operating-system package manager before running the camera integration.

```sh
python -m pip install -e ".[dev,simulator,perception]"
MUJOCO_GL=osmesa OASSE_NATIVE_CAMERA_TESTS=1 python -m pytest tests -q
MUJOCO_GL=osmesa python scripts/run_native_vision_demo.py --output native-vision.json --artifacts-dir demo-output/native-vision
```

The GL backend must be selected before importing MuJoCo. Non-Linux rendering backends need their own validation; this CI proof uses Linux CPU inference and OSMesa. The simulation camera requires capture on the thread which owns its render context. The context is closed after each case.

## What is real and what remains a baseline

`MuJoCoRGBCamera` produces rendered RGB8 frames, rather than strings standing in for camera data. A visual-only black mark on the cube changes those pixels. `OpenVINOIRRunner` reads, validates and compiles real IR bytes and runs a native infer request. `MuJoCoCartesianRuntime` applies velocity controls and advances native physics with `mj_step`.

The included IR graph is an independently authored reference-image difference calculation, not a trained Anomalib detector. It computes mean absolute RGB difference per pixel and a decoder localizes changes over a declared threshold. A moved object, lighting change or camera change can also produce differences. It does not classify manufacturing defects in general. Its confidence field is a declared demo value, explicitly labeled as not calibrated; its anomaly score is not a probability.

Workspace clearance and object geometry are explicit simulator-ground-truth context, not inferred from the image. This remains a Cartesian carrier scene with a scripted proposal generator, not an SO-101 or bimanual arm, a trained LeRobot/VLA, or a successful grasp-and-sort demonstration. The defective-cube case selects the reject destination in the proposal and executes a short diagnostic motion; it does not physically transport the cube into a bin. Gatekeeper's production service is still external and has not been contacted by this CI run. The outage scenario exercises its HTTP adapter with a declared mock transport.

## Native model contract

`providers/openvino_runtime.py` defines `RGBSpec`, `RGBFrame`, `OpenVINOIRRunner`, `NativeOpenVINOPerception` and the reference-only graph/decoder. Input is exactly width times height times three raw RGB8 bytes, converted to static float32 NCHW in [0,1]. JPEG, BGR, floating-point image buffers, automatic resizing and arbitrary normalization are not silently accepted. Dimensions must be in [8,512]. Models need one matching input and bounded static outputs. A different trained-model preprocessing contract must be implemented and tested explicitly.

IR definition and weights are read into bounded memory, hashed together with length delimiters, and the exact hashed bytes are compiled. An optional expected hash is checked before compilation. This binds the artifact but does not establish trust in its author or sandbox the native model parser. Load only trusted local artifacts. The requested device is explicit, and actual execution devices and OpenVINO version are recorded. GPU and NPU execution are not established by the CPU tests, and unsupported devices fail rather than silently falling back to mocks or AUTO.

Inputs and outputs are copied. Capture integers cannot be coerced into zero-filled synthetic images. Invalid frame metadata is rejected before inference. A shared runner serializes its native infer requests and returns a detached provenance record with each result, so another call cannot overwrite the recorded latency or inference index. `native_inference_ms` measures native inference and output validation, excluding model compilation, rendering and image preprocessing. It is not a whole-system latency benchmark.

## Hardening completed before this phase

The adversarial baseline added 24 regressions and reproduced failures while all original 129 tests remained green. They exposed mutable proposal aliasing after receipt sealing, weak direct-evaluation API inputs, receipt payload aliasing and concurrent chain corruption, missing evaluation receipts, an empty actor allowlist enabling defaults, invalid authority timing values and lost context on scene-sampling errors.

The refactor separates validated snapshots, authority response handling, dispatch reservation, invocation, receipts and the dashboard. The actuator gets an isolated action copy, not the object in the sealed decision. Cooperative native step guards verify the action fingerprint and evidence lease before further physics steps. Detected mutation revokes the next step and is not reported as confirmed success. Receipt appends use an in-process lock and strict finite JSON snapshots. A corrupted prior chain blocks new dispatch; the HTTP API reports it as unavailable rather than running anyway.

The direct evaluation API now shares input validation and seals its decision without invoking the actuator. Invalid input receives a generic client error without raw exception details. Replay reservations are atomic even when the same guard is shared among in-process orchestrators. Evidence leases use a monotonic deadline in addition to capture wall time so a stalled/backward wall clock cannot extend an existing lease during evaluation or execution.

These are in-process controls for trusted integration components, not isolation against malicious code holding direct simulator/actuator references. Anti-replay state and receipts remain in memory, not durable across restart. Scene comparison is at launch, not continuous collision avoidance. Physical braking, emergency stops, source authentication and calibrated vision remain separate integration requirements.

## Automated evidence

The native CI job requires both OpenVINO and MuJoCo imports before testing, then exercises ten rendered-camera scenarios: fresh, marked cube, overspeed, stale, future-dated, occupied, low confidence, changed scene, replay and authority outage. Positive cases must advance physics; blocked cases must not. Replay adds no steps after the first valid execution. Each case validates receipt chaining and preserves artifact provenance, pixel hashes and explicit outcomes.

The GitHub Actions `native-perception-verification` artifact contains JUnit results, dependency versions, native-vision JSON with receipts, exported IR fixtures and exact observed images in PPM format. These artifacts are retained for 14 days by CI. The default `test` job still validates Docker build/startup and real HTTP responses for all four verdicts, and the separate `simulator` job exercises native dynamics without depending on OpenVINO.

## Implementation references

The implementation follows the official OpenVINO Core `read_model` bytes overload and InferRequest copying controls, and MuJoCo's Python Renderer and `mjv_initGeom` APIs. No source or robot assets from the external LeRobot tutorial are copied into this repository. All authored integration code remains under this repository's MIT license; proprietary Gatekeeper technology is not distributed.
