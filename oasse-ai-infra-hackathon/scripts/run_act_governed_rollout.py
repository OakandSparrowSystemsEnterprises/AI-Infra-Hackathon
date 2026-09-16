from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
import uuid
from pathlib import Path


JOINTS = (
    "shoulder_pan.pos",
    "shoulder_lift.pos",
    "elbow_flex.pos",
    "wrist_flex.pos",
    "wrist_roll.pos",
    "gripper.pos",
)


def parse_caps(value: str) -> list[float]:
    caps = [float(item.strip()) for item in value.split(",")]
    if len(caps) != len(JOINTS) or any(cap <= 0 for cap in caps):
        raise argparse.ArgumentTypeError("--caps must contain six positive comma-separated values")
    return caps


def post_json(url: str, body: dict) -> dict:
    payload = json.dumps(body, separators=(",", ":"), allow_nan=False).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read())


def envelope_digest(action_id: str, evidence_id: str, joint_action: dict[str, float]) -> str:
    payload = {
        "action_id": action_id,
        "evidence_id": evidence_id,
        "joint_action": {key: joint_action[key] for key in sorted(joint_action)},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a closed-loop ACT policy where every bounded SO-101 command receives a fresh authority decision."
    )
    parser.add_argument("--policy-dir", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--robot-port", required=True)
    parser.add_argument("--robot-id", required=True)
    parser.add_argument("--camera-index", type=int, required=True)
    parser.add_argument("--camera-id", default="onsite-rgb-camera")
    parser.add_argument("--authority-url", default="http://127.0.0.1:8000/v1/evaluate")
    parser.add_argument("--task", default="Pick the large LEGO block and drop it in the pink bowl.")
    parser.add_argument("--caps", type=parse_caps, default=parse_caps("11.43,5,5,3.47,2.64,5"))
    parser.add_argument("--max-steps", type=int, default=600)
    parser.add_argument("--speed-mps", type=float, default=0.05)
    parser.add_argument("--state-margin-deg", type=float, default=5.0)
    parser.add_argument("--workspace-clear", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Required for physical rollout.")
    parser.add_argument("--output", type=Path, default=Path("act-governed-rollout.json"))
    args = parser.parse_args()

    if not args.execute or not args.workspace_clear:
        raise SystemExit("Refusing rollout without both --execute and --workspace-clear")
    if args.max_steps <= 0:
        raise SystemExit("--max-steps must be positive")

    import cv2
    import numpy as np
    import pandas as pd
    import torch
    from lerobot.policies import make_pre_post_processors
    from lerobot.policies.act import ACTPolicy
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

    parquet_files = sorted(args.dataset_root.glob("data/**/*.parquet"))
    if not parquet_files:
        raise SystemExit(f"No parquet files found under {args.dataset_root / 'data'}")
    frames = pd.concat([pd.read_parquet(path) for path in parquet_files], ignore_index=True)
    states = np.vstack(frames["observation.state"].apply(np.asarray))
    actions = np.vstack(frames["action"].apply(np.asarray))
    state_min, state_max = states.min(axis=0), states.max(axis=0)
    action_min, action_max = actions.min(axis=0), actions.max(axis=0)

    policy = ACTPolicy.from_pretrained(args.policy_dir)
    policy.to("xpu")
    policy.eval()
    pre, post = make_pre_post_processors(
        policy_cfg=policy.config,
        pretrained_path=args.policy_dir,
        preprocessor_overrides={"device_processor": {"device": "xpu"}},
    )
    # Reset once per environment reset. select_action() then consumes the queued ACT chunk.
    policy.reset()

    robot = SO101Follower(
        SO101FollowerConfig(
            port=args.robot_port,
            id=args.robot_id,
            cameras={},
            disable_torque_on_disconnect=False,
        )
    )
    robot.connect(calibrate=False)

    camera = cv2.VideoCapture(args.camera_index)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not camera.isOpened():
        robot.disconnect()
        raise RuntimeError("CAMERA_OPEN_FAILED")
    for _ in range(3):
        camera.read()

    proof: dict = {
        "schema": "oasse.act-governed-rollout.v1",
        "policy": str(args.policy_dir),
        "dataset": str(args.dataset_root),
        "policy_chunk_size": policy.config.chunk_size,
        "policy_n_action_steps": policy.config.n_action_steps,
        "max_steps": args.max_steps,
        "steps": [],
        "status": "RUNNING",
        "started_at_ms": int(time.time() * 1000),
    }

    def persist() -> None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    def wait_robot_stable(timeout_s: float = 2.0, tolerance_deg: float = 0.35, required: int = 3) -> dict[str, float]:
        deadline = time.monotonic() + timeout_s
        previous = None
        stable_count = 0
        latest = None
        while time.monotonic() < deadline:
            observation = robot.get_observation()
            latest = {key: float(observation[key]) for key in JOINTS}
            if previous is not None:
                max_motion = max(abs(latest[key] - previous[key]) for key in JOINTS)
                stable_count = stable_count + 1 if max_motion <= tolerance_deg else 0
                if stable_count >= required:
                    return latest
            previous = latest
            time.sleep(0.05)
        if latest is None:
            raise RuntimeError("ROBOT_STATE_UNAVAILABLE")
        return latest

    return_code = 1
    try:
        caps = np.asarray(args.caps, dtype=np.float32)
        for step_index in range(args.max_steps):
            stable = wait_robot_stable()
            state = np.asarray([stable[key] for key in JOINTS], dtype=np.float32)
            if np.any(state < state_min - args.state_margin_deg) or np.any(state > state_max + args.state_margin_deg):
                proof["status"] = "STOPPED_OOD_STATE"
                proof["ood_state"] = state.tolist()
                persist()
                break

            ok, frame = camera.read()
            captured_at_ms = int(time.time() * 1000)
            if not ok or frame is None:
                raise RuntimeError("CAMERA_READ_FAILED")
            frame_hash = hashlib.sha256(frame.tobytes()).hexdigest()
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0

            processed = pre(
                {
                    "observation.images.front": image.unsqueeze(0),
                    "observation.state": torch.tensor(state).unsqueeze(0),
                    "task": [args.task],
                }
            )
            with torch.inference_mode():
                raw = post(policy.select_action(processed)).detach().cpu()[0].numpy()

            range_bounded = np.clip(raw, action_min, action_max)
            bounded_delta = np.clip(range_bounded - state, -caps, caps)
            target_array = state + bounded_delta
            raw_map = {key: float(value) for key, value in zip(JOINTS, raw)}
            target = {key: float(value) for key, value in zip(JOINTS, target_array)}

            evidence_id = f"ev-act-{uuid.uuid4().hex[:12]}"
            action_id = f"act-act-{uuid.uuid4().hex[:12]}"
            requested_at_ms = int(time.time() * 1000)
            envelope = envelope_digest(action_id, evidence_id, target)
            evidence = {
                "evidence_id": evidence_id,
                "captured_at_ms": captured_at_ms,
                "confidence": 0.99,
                "workspace_clear": True,
                "anomaly_score": 0.0,
                "target_label": "large_lego_block",
                "camera_id": args.camera_id,
                "frame_hash": frame_hash,
                "frame_sequence": step_index + 1,
                "metadata": {"source": "act-governed-rollout", "operator_interlock": True},
            }
            action = {
                "action_id": action_id,
                "actor_id": "vla-planner-1",
                "action_type": "pick_place",
                "target_bin": "accept",
                "speed_mps": args.speed_mps,
                "evidence_id": evidence_id,
                "requested_at_ms": requested_at_ms,
                "object_id": "large-lego-block",
                "trajectory": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
                "metadata": {
                    "policy": "ACT",
                    "policy_checkpoint": str(args.policy_dir),
                    "raw_joint_action": raw_map,
                    "joint_action": target,
                    "execution_envelope_sha256": envelope,
                },
            }

            decision = post_json(args.authority_url, {"evidence": evidence, "action": action})
            if decision.get("verdict") != "ALLOW":
                proof["status"] = f"STOPPED_AUTHORITY_{decision.get('verdict', 'UNKNOWN')}"
                proof["steps"].append({"step": step_index, "decision": decision})
                persist()
                break

            authorized = decision.get("authorized_action")
            if not authorized:
                raise RuntimeError("ALLOW_WITHOUT_AUTHORIZED_ACTION")
            if authorized["metadata"]["joint_action"] != target:
                raise RuntimeError("AUTHORIZED_TARGET_CHANGED")
            if authorized["metadata"]["execution_envelope_sha256"] != envelope:
                raise RuntimeError("ENVELOPE_BINDING_FAILED")

            pre_dispatch = robot.get_observation()
            before = {key: float(pre_dispatch[key]) for key in JOINTS}
            if any(abs(before[key] - float(state[index])) > 2.0 for index, key in enumerate(JOINTS)):
                raise RuntimeError("STATE_CHANGED_BEFORE_DISPATCH")

            send_result = robot.send_action(target)
            deadline = time.monotonic() + 2.0
            after = before
            while time.monotonic() < deadline:
                time.sleep(0.05)
                after_obs = robot.get_observation()
                after = {key: float(after_obs[key]) for key in JOINTS}
                if all(
                    abs(target[key] - after[key]) <= 3.0
                    for key in JOINTS
                    if abs(target[key] - before[key]) >= 1.0
                ):
                    break

            if any(
                abs(target[key] - after[key]) > 3.0
                for key in JOINTS
                if abs(target[key] - before[key]) >= 1.0
            ):
                raise RuntimeError("ENCODER_VERIFICATION_FAILED")

            proof["steps"].append(
                {
                    "step": step_index,
                    "captured_at_ms": captured_at_ms,
                    "frame_hash": frame_hash,
                    "evidence_id": evidence_id,
                    "action_id": action_id,
                    "decision_id": decision["decision_id"],
                    "verdict": decision["verdict"],
                    "reason_codes": decision.get("reason_codes", []),
                    "execution_envelope_sha256": envelope,
                    "raw_act": raw_map,
                    "authorized_target": target,
                    "before": before,
                    "after": after,
                    "send_result": send_result,
                }
            )
            persist()
        else:
            proof["status"] = "MAX_STEPS_REACHED"

        if proof["status"] == "RUNNING":
            proof["status"] = "ROLLOUT_COMPLETE"
        return_code = 0 if proof["status"] in {"ROLLOUT_COMPLETE", "MAX_STEPS_REACHED"} else 1
    except KeyboardInterrupt:
        proof["status"] = "OPERATOR_ABORT"
        return_code = 0
    except Exception as exc:
        proof["status"] = "FAILED"
        proof["error"] = repr(exc)
        raise
    finally:
        proof["finished_at_ms"] = int(time.time() * 1000)
        persist()
        camera.release()
        robot.disconnect()
        print(json.dumps({"status": proof["status"], "steps": len(proof["steps"]), "output": str(args.output)}, indent=2))

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
