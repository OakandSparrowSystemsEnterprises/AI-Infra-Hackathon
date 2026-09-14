# Onsite integration runbook

Start from the tested repository commit and preserve the provided Intel environment. `python scripts/check_environment.py --native --output /tmp/environment.json` reports imports, versions and available OpenVINO devices without connecting a camera or moving a robot. Use the organizer's stack verification script and supported Physical AI Studio environment before changing dependencies. The supplied workstation, trained model, camera calibration and controller must be checked on the actual machine.

## Jackson: capture and anomaly model

Bind the actual camera to `OpenCVRGBSource` or an equivalent `RGBFrame` source. Supply the declared image dimensions, RGB8 bytes, monotonically increasing sequence and truthful capture timing. Provide fresh workspace/context data and calibrated geometry through `CameraContext`; missing context must remain an error. Preserve the camera's own buffering/exposure limitations in the recorded provenance.

Load the approved local Anomalib XML/BIN export through `OpenVINOIRRunner` with its expected artifact digest and explicit CPU, GPU or NPU device. Bind `AnomalibDecoder` to the actual export's score/map names and held-out calibration thresholds. Confirm that preprocessing is not performed twice. The runner expects static NCHW float32 RGB/255; a different export requires a reviewed conversion, not silent reshaping. Test normal and defective images from the actual camera before allowing a proposal to dispatch. See `JACKSON_PERCEPTION.md` and `PHASE4_INSPECTION.md` for the normalized evidence contract.

## Planner and arm boundary

Our `ProposedAction.trajectory` contains Cartesian XYZ points in meters. LeRobot joint targets are not interchangeable with this representation. Use the installed robot model and calibration for the conversion, and declare the complete physical command before authorization. Retain the controller's own joint, velocity and relative-target limits. Intercept at the last point after mapping/limiting and before the actual motor write. A command changed after authorization must be held or re-evaluated; it must not be relabeled as the approved action.

The current SO follower interface may return the actual clipped target rather than the input target. Record that result accurately, but do not treat it as evidence that an object reached its bin. Confirm the installed implementation, not just its public current documentation. The physical arm path is not automatically wired by the Cartesian simulator or its idealized suction recipe.

Connect `InspectionTask` to the supervised controller and a new, independent task observation. Verification must report object identity, observed bin, released state, object speed, observation source and capture time. Report unknown when a motor call times out or effects are ambiguous. Do not retry an ambiguous task automatically. Safe stop, workspace control, operator approval and hardware emergency-stop procedures remain the controller/operator's responsibilities.

## Live authority and recording

Run the non-actuating live probe from `GATEKEEPER_LIVE_ACCEPTANCE.md` against the intended policy. Keep live and reference runs clearly labeled. Preserve a trace showing normal sorting, defective sorting and a denied or held proposed action. Record which layer stopped the action and whether any movement preceded interruption.

Complete a copy of `config/onsite-acceptance.example.json` only from actual observations and retain the supporting notes. These flags are operator attestations, not an independent safety certification. Pass the acceptance record and live-probe report to `rehearse_submission.py` to obtain a consolidated readiness report. Native rehearsal success alone never declares the onsite submission ready.

## Before handing the entry to judges

Freeze the tested commit, verify the evidence bundle, record the short demonstration, fill the video and judge-access fields in `submission.json`, and test repository access using the intended judge-facing URL. Keep proprietary Gatekeeper source, production credentials, private integrations and undistributed technology outside the MIT integration repository. The tools create a candidate package; the team must still review and submit it through the organizer's actual form.

Primary implementation references: https://docs.openedgeplatform.intel.com/dev/edge-ai-suites/robotics-ai-suite/resources/hackathon_resources.html ; https://anomalib.readthedocs.io/en/latest/markdown/guides/reference/deploy/ ; https://github.com/huggingface/lerobot/blob/main/src/lerobot/robots/so_follower/so_follower.py . These are references, not a guarantee of the installed event versions.
