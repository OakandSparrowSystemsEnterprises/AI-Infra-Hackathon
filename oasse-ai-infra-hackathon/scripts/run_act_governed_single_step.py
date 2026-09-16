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


def parse_camera_source(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value


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
        description="Generate one ACT action, bind it through authority, and optionally execute one bounded SO-101 step."
    )
    parser.add_argument("--policy-dir", type=Path, required=True)
    parser.add_argument("--robot-port", required=True)
    parser.add_argument("--robot-id", required=True)
    parser.add_argument(
        "--camera",
        "--camera-index",
        dest="camera",
        required=True,
        help="OpenCV camera index (for example 1) or device path (for example /dev/video1).",
    )
    parser.add_argument("--camera-id", default="onsite-rgb-camera")
    parser.add_argument("--authority-url", default="http://127.0.0.1:8000/v1/evaluate")
    parser.add_argument("--task", default="Pick the large LEGO block and drop it in the pink bowl.")
    parser.add_argument("--device", default="xpu", help="Torch/LeRobot policy device. Intel onsite default: xpu.")
    parser.add_argument("--caps", type=parse_caps, default=parse_caps("11.43,5,5,3.47,2.64,5"))
    parser.add_argument("--speed-mps", type=float, default=0.05)
    parser.add_argument("--workspace-clear", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Physically send the authority-approved action.")
    parser.add_argument("--output", type=Path, default=Path("act-governed-single-step.json"))
    args = parser.parse_args()

    if args.execute and not args.workspace_clear:
        raise SystemExit("Refusing physical execution unless --workspace-clear is explicitly supplied")

    import cv2
    import torch
    from lerobot.policies import make_pre_post_processors
    from lerobot.policies.act import ACTPolicy
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

    policy = ACTPolicy.from_pretrained(args.policy_dir)
    policy.to(args.device)
    policy.eval()
    pre, post = make_pre_post_processors(
        policy_cfg=policy.config,
        pretrained_path=args.policy_dir,
        preprocessor_overrides={"device_processor": {"device": args.device}},
    )

    robot = SO101Follower(
        SO101FollowerConfig(
            port=args.robot_port,
            id=args.robot_id,
            cameras={},
            disable_torque_on_disconnect=False,
        )
    )
    robot.connect(calibrate=False)

    camera_source = parse_camera_source(args.camera)
    proof: dict = {
        "schema": "oasse.act-governed-single-step.v2",
        "policy": str(args.policy_dir),
        "device": args.device,
        "camera_source": str(camera_source),
        "workspace_clear": args.workspace_clear,
        "execute_requested": args.execute,
    }

    try:
        observation = robot.get_observation()
        state = torch.tensor([float(observation[key]) for key in JOINTS], dtype=torch.float32)

        camera = cv2.VideoCapture(camera_source)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        ok, frame = camera.read()
        captured_at_ms = int(time.time() * 1000)
        camera.release()
        if not ok or frame is None:
            raise RuntimeError(f"CAMERA_READ_FAILED: {camera_source!r}")

        frame_hash = hashlib.sha256(frame.tobytes()).hexdigest()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0

        processed = pre(
            {
                "observation.images.front": image.unsqueeze(0),
                "observation.state": state.unsqueeze(0),
                "task": [args.task],
            }
        )
        policy.reset()
        with torch.inference_mode():
            raw = post(policy.select_action(processed)).detach().cpu()[0]

        caps = torch.tensor(args.caps, dtype=torch.float32)
        bounded_delta = torch.maximum(torch.minimum(raw - state, caps), -caps)
        bounded = state + bounded_delta
        raw_map = {key: float(value) for key, value in zip(JOINTS, raw.tolist())}
        target = {key: float(value) for key, value in zip(JOINTS, bounded.tolist())}

        evidence_id = f"ev-act-{uuid.uuid4().hex[:12]}"
        action_id = f"act-act-{uuid.uuid4().hex[:12]}"
        requested_at_ms = int(time.time() * 1000)
        envelope = envelope_digest(action_id, evidence_id, target)

        evidence = {
            "evidence_id": evidence_id,
            "captured_at_ms": captured_at_ms,
            "confidence": 0.99,
            "workspace_clear": args.workspace_clear,
            "anomaly_score": 0.0,
            "target_label": "large_lego_block",
            "camera_id": args.camera_id,
            "frame_hash": frame_hash,
            "metadata": {
                "source": "act-governed-single-step",
                "operator_interlock": args.workspace_clear,
            },
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
        proof.update(
            {
                "evidence_id": evidence_id,
                "action_id": action_id,
                "frame_hash": frame_hash,
                "raw_act": raw_map,
                "authorized_candidate": target,
                "execution_envelope_sha256": envelope,
                "decision": decision,
            }
        )

        if decision.get("verdict") != "ALLOW":
            proof["status"] = "NOT_EXECUTED_AUTHORITY_BLOCK"
            return_code = 0
        else:
            authorized = decision.get("authorized_action")
            if not authorized:
                raise RuntimeError("ALLOW_WITHOUT_AUTHORIZED_ACTION")
            if authorized["metadata"]["joint_action"] != target:
                raise RuntimeError("AUTHORIZED_TARGET_CHANGED")
            if authorized["metadata"]["execution_envelope_sha256"] != envelope:
                raise RuntimeError("ENVELOPE_BINDING_FAILED")

            if not args.execute:
                proof["status"] = "AUTHORIZED_DRY_RUN"
                return_code = 0
            else:
                before_obs = robot.get_observation()
                before = {key: float(before_obs[key]) for key in JOINTS}
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

                verified = all(
                    abs(target[key] - after[key]) <= 3.0
                    for key in JOINTS
                    if abs(target[key] - before[key]) >= 1.0
                )
                proof.update(
                    {
                        "before": before,
                        "after": after,
                        "send_result": send_result,
                        "status": "PHYSICALLY_VERIFIED" if verified else "COMMAND_SENT_UNVERIFIED",
                    }
                )
                return_code = 0 if verified else 1
    finally:
        robot.disconnect()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    print(json.dumps({"status": proof.get("status"), "output": str(args.output)}, indent=2))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
