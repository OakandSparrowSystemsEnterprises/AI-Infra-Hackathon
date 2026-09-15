# Jackson: camera and perception handoff

Your part answers what the camera sees, whether the object differs from an acceptable object, and where the visible anomaly is. Gatekeeper, not perception, decides whether the proposed action may execute.

Start in `src/oasse_physical_ai/providers/openvino_runtime.py`. `OpenVINOIRRunner` already loads and executes a trusted local OpenVINO IR artifact. `NativeOpenVINOPerception` converts its output into the evidence contract. `RGBFrame` preserves the image bytes, capture time, camera identity, sequence and explicitly sourced workspace context. The simulation example uses `MuJoCoRGBCamera` from `providers/mujoco_camera.py` so you can exercise the interface without the physical camera.

Run the native vision smoke script using the instructions in `docs/PHASE3_NATIVE_PERCEPTION.md`. Its current detector is only a deterministic comparison with a clean reference image. It is a working integration fixture, not the trained anomaly model you are being asked to provide.

Replace the reference IR graph and decoder with the selected trained detector's exported model and validated output mapping. Record its exact preprocessing, output shapes, model hash, confidence meaning and device. The existing runner's input is RGB8 converted to float32 NCHW divided by 255. Do not assume this matches a new model without checking. Add test images with normal cubes and black-marked cubes, and report the observed anomaly localization and errors rather than inferring accuracy from the synthetic demo.

The camera source must not refresh timestamps on old frames. Missing workspace information is not evidence of a clear workspace. Supply workspace context from its actual source, or fail closed. Geometry and workspace information supplied by the simulator in today's example must not be relabeled as camera inference when the real camera is connected.

Keep raw tensors and image arrays outside receipt metadata. The adapter converts numerical outputs to ordinary finite Python values and binds observations to the exact frame hash. Do not change Gatekeeper decisions, policy thresholds, replay state or actuator code to make a perception test pass. Your success condition is a real frame becoming accurate, traceable evidence behind the existing interface.

## Trained model workflow

Training and export stay outside this repository. Datasets, checkpoints, backbone weights and exported XML/BIN are not committed here unless redistribution is separately approved.

Export the trained detector at the exact camera resolution. The OpenVINO export path runs through ONNX, so `onnx` must be installed alongside `anomalib` and `openvino`.

```sh
anomalib export --model Padim --export_type openvino --ckpt_path <CKPT> --input_size "[<H>,<W>]"
```

An Anomalib export is not directly consumable by `OpenVINOIRRunner`. Its batch dimension stays dynamic even when `input_size` is given, and it exposes boolean `pred_label` and `pred_mask` tensors beside the numeric outputs, which the runner correctly refuses as non-numeric. Prepare the artifact instead of relaxing the runner:

```sh
python scripts/prepare_anomalib_ir.py --source <export.xml> --target <prepared.xml> \
  --height <H> --width <W> --provenance onsite/prepared-ir.json
```

Preparation pins the batch to one and exposes only `pred_score` and `anomaly_map`. It reloads and re-verifies the emitted artifact, and it is byte deterministic, so the printed `artifact_digest` is a stable pin. Record the source and prepared hashes with the digest. Never run the integration with an unpinned artifact: an unpinned tampered artifact will load and infer without complaint, and the digest is the check that catches it.

The exported graph carries Anomalib's preprocessing, including the ImageNet normalization. It expects plain RGB divided by 255, which is exactly what `RGBSpec.tensor()` already produces. Do not normalize before the runner and do not change `RGBSpec.tensor()` to match a model; a double-normalized frame produces confident nonsense rather than an error.

Thresholds are inputs, not defaults. Calibrate `image_threshold` and `pixel_threshold` on a held-out split, keep `pixel_threshold` at or below `image_threshold`, and record a `calibration_id` bound to the calibration data, the artifact digest and the camera configuration. If the pixel threshold sits above the image threshold, a defect can score above the image threshold with no pixel above the pixel threshold, and `AnomalibDecoder` refuses it rather than emitting an unlocalized defect.

```sh
python scripts/run_live_perception.py --model <prepared.xml> --expected-digest <digest> \
  --height <H> --width <W> --device CPU --camera-id <id> \
  --camera-index 0 --context-entrypoint <module>:<callable> \
  --image-threshold <value> --pixel-threshold <value> --calibration-id <id> \
  --output onsite/live-perception.json
```

Workspace context must come from a real source. OpenCV ingress requires `--context-entrypoint` naming a callable that returns a `CameraContext`; there is no default and no stub. Sponsor ingress uses `--capture-entrypoint` instead, and the sponsor callback carries its own explicit timing and workspace context through `SponsorRGBSource`, so `--context-entrypoint` does not apply and is rejected. The two ingress modes are mutually exclusive.

Record the device actually used. The runner reports `execution_devices` from the compiled model, which is the value to keep, rather than the device that was requested. `config/perception.example.json` shows the full configuration surface.

These steps establish traceability, not accuracy. Any detection claim is bounded by the object, camera, lighting and environment actually tested.
