# Onsite ACT + SO-101 Handoff

This document records the September 15, 2026 Intel onsite state so the next operator can resume without reconstructing the hardware mapping or repeating exploratory work.

## Hardware identity

The two SO-101-class devices were identified from raw Feetech encoder reads rather than `/dev/ttyACM*` numbering, which changed during the session.

- **Right 5 V leader / hand controller**: USB serial `5B79018322`
- **Left 12 V follower / LEGO arm**: USB serial `5B79018350`
- Event calibration IDs used after the hardware mapping was corrected:
  - leader: `lego_leader_322`
  - follower: `lego_follower_350`

Prefer `/dev/serial/by-id/...` over `/dev/ttyACM*` when reproducing the event setup. Calibration files are local machine state and are intentionally not committed.

## Event runtime

Verified onsite components included:

- LeRobot 0.6.1 in the robot-control environment
- Intel Arc B390 through PyTorch XPU for ACT training/inference
- OpenVINO 2026.3 on the Intel development environment
- real SO-101 follower actuation with encoder readback
- local HTTP pre-execution authority service using `ReferenceAuthorityEngine`

The local authority service is a reference engine behind the same pre-execution HTTP boundary. It is **not** the separate proprietary production Gatekeeper runtime.

## What was physically proven

The following sequence was completed on the event hardware:

1. Real robot state and RGB camera input were read.
2. A trained ACT policy produced a six-joint action.
3. A deterministic per-joint limiter bounded the proposed movement.
4. The exact bounded joint action was SHA-256-bound to evidence and action identities.
5. `workspace_clear=false` produced `DENY / WORKSPACE_OCCUPIED` with no physical handoff.
6. `workspace_clear=true` produced `ALLOW / POLICY_SATISFIED`.
7. The returned authorized action preserved the exact joint command and execution-envelope digest.
8. One authority-approved ACT action was dispatched to the follower.
9. Encoder readback verified physical convergence and the proof status was `PHYSICALLY_VERIFIED`.

A later closed-loop runner completed 600 individually authority-approved actions without an authority or actuator-path collapse. That run did **not** complete the LEGO task and must not be represented as task success.

## Dataset finding

The first ten-episode LeRobot dataset mixed idle and manipulation data. Offline analysis found:

- episodes 0-2: essentially idle
- episodes 3-4: arm movement with negligible gripper signal
- episodes 5, 6, 8, 9: strongest manipulation/gripper signal
- episode 7: substantial arm motion but little gripper movement

The first ACT model learned a stable/hold attractor from the mixed dataset. The clean retraining plan uses episodes `[5,6,8,9]` and reduces `n_action_steps` so the policy replans from fresh observations more frequently.

At handoff time, the clean-v2 training job had been started but full autonomous LEGO pick-and-drop had **not yet been proven**.

## Camera note

Linux video indices re-enumerated during the event. The recorded dataset originally used a 640x480 RGB OpenCV stream, but later `/dev/video4` was no longer that stream. Re-probe cameras after reboot/device changes instead of assuming a fixed `/dev/videoN` index.

Example probe:

```bash
python - <<'PY'
import cv2, glob, re
for dev in sorted(glob.glob('/dev/video*'), key=lambda x: int(re.search(r'\d+$', x).group())):
    idx = int(re.search(r'\d+$', dev).group())
    cap = cv2.VideoCapture(idx)
    ok, frame = cap.read() if cap.isOpened() else (False, None)
    cap.release()
    print(dev, ok, None if frame is None else frame.shape)
PY
```

Both governed ACT runners accept either a numeric camera index or a device path through `--camera` (`--camera-index` remains an alias).

## Reusable repository runners

The repository contains tracked, parameterized scripts rather than the event machine's scratch files:

- `scripts/analyze_lerobot_dataset.py`
- `scripts/check_act_checkpoint.py`
- `scripts/run_act_governed_single_step.py`
- `scripts/run_act_governed_rollout.py`

Example event-style single-step invocation:

```bash
python scripts/run_act_governed_single_step.py \
  --policy-dir /path/to/pretrained_model \
  --robot-port /dev/serial/by-id/usb-1a86_USB_Single_Serial_5B79018350-if00 \
  --robot-id lego_follower_350 \
  --camera /dev/video1 \
  --device xpu \
  --workspace-clear \
  --execute \
  --output /tmp/act-governed-step.json
```

The camera path above is illustrative. Probe the current machine first.

For the clean retrain, derive state/action guard ranges from the same episode subset used for training:

```bash
python scripts/run_act_governed_rollout.py \
  --policy-dir /path/to/pretrained_model \
  --dataset-root "$HOME/Downloads/lego_pick_bowl_dataset" \
  --dataset-episodes 5,6,8,9 \
  --robot-port /dev/serial/by-id/usb-1a86_USB_Single_Serial_5B79018350-if00 \
  --robot-id lego_follower_350 \
  --camera /dev/video1 \
  --device xpu \
  --workspace-clear \
  --execute \
  --output /tmp/act-governed-rollout.json
```

`--dataset-episodes` is important for the clean-v2 model: the rollout's state and action range guards are calculated from the selected episodes rather than from the contaminated ten-episode pool.

The rollout does not infer task success. `MAX_STEPS_REACHED` is an incomplete run and exits non-zero; `OPERATOR_ABORT` is also an incomplete run. A full autonomous success claim requires separate visible task-completion evidence plus the governed proof record.

## Clean retraining configuration

The onsite clean-model plan was:

```bash
lerobot-train \
  --dataset.repo_id=oasse/lego_pick_bowl_local \
  --dataset.root="$HOME/Downloads/lego_pick_bowl_dataset" \
  --dataset.episodes='[5,6,8,9]' \
  --policy.type=act \
  --policy.device=xpu \
  --policy.chunk_size=100 \
  --policy.n_action_steps=20 \
  --policy.push_to_hub=false \
  --output_dir="$HOME/Downloads/act_lego_clean_v2" \
  --job_name=act_lego_clean_v2 \
  --batch_size=4 \
  --num_workers=2 \
  --steps=15000 \
  --log_freq=100 \
  --env_eval_freq=0 \
  --save_checkpoint=true \
  --save_freq=3000 \
  --wandb.enable=false
```

Model weights, datasets, calibration files and event-machine receipts remain local/generated artifacts and are intentionally excluded from Git.

## Claim boundaries

Do not overstate the onsite result:

- Proven: governed learned-policy physical step with encoder verification.
- Proven: explicit DENY path with no physical handoff.
- Proven: ACT training/inference on Intel XPU and real SO-101 actuation.
- Not yet proven at handoff: autonomous end-to-end LEGO pick-and-drop success.
- The MVTec PaDiM artifact used earlier was an OpenVINO runtime/integration bring-up model, not a LEGO detector.
- The onsite HTTP authority was the repository `ReferenceAuthorityEngine`, not production Gatekeeper.

See `ONSITE_REVIEW_CHECKLIST.md` before another physical run.
