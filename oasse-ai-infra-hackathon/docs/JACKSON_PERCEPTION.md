# Jackson: camera and perception handoff

Your part answers what the camera sees, whether the object differs from an acceptable object, and where the visible anomaly is. Gatekeeper, not perception, decides whether the proposed action may execute.

Start in `src/oasse_physical_ai/providers/openvino_runtime.py`. `OpenVINOIRRunner` already loads and executes a trusted local OpenVINO IR artifact. `NativeOpenVINOPerception` converts its output into the evidence contract. `RGBFrame` preserves the image bytes, capture time, camera identity, sequence and explicitly sourced workspace context. The simulation example uses `MuJoCoRGBCamera` from `providers/mujoco_camera.py` so you can exercise the interface without the physical camera.

Run the native vision smoke script using the instructions in `docs/PHASE3_NATIVE_PERCEPTION.md`. Its current detector is only a deterministic comparison with a clean reference image. It is a working integration fixture, not the trained anomaly model you are being asked to provide.

Replace the reference IR graph and decoder with the selected trained detector's exported model and validated output mapping. Record its exact preprocessing, output shapes, model hash, confidence meaning and device. The existing runner's input is RGB8 converted to float32 NCHW divided by 255. Do not assume this matches a new model without checking. Add test images with normal cubes and black-marked cubes, and report the observed anomaly localization and errors rather than inferring accuracy from the synthetic demo.

The camera source must not refresh timestamps on old frames. Missing workspace information is not evidence of a clear workspace. Supply workspace context from its actual source, or fail closed. Geometry and workspace information supplied by the simulator in today's example must not be relabeled as camera inference when the real camera is connected.

Keep raw tensors and image arrays outside receipt metadata. The adapter converts numerical outputs to ordinary finite Python values and binds observations to the exact frame hash. Do not change Gatekeeper decisions, policy thresholds, replay state or actuator code to make a perception test pass. Your success condition is a real frame becoming accurate, traceable evidence behind the existing interface.
