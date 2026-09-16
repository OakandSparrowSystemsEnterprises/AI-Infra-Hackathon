from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


JOINT_NAMES = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
)


def load_frames(root: Path) -> pd.DataFrame:
    parquet_files = sorted(root.glob("data/**/*.parquet"))
    if not parquet_files:
        raise SystemExit(f"No parquet files found under {root / 'data'}")
    return pd.concat([pd.read_parquet(path) for path in parquet_files], ignore_index=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize motion and gripper signal in a LeRobot dataset without touching robot hardware."
    )
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument(
        "--candidate-gripper-span",
        type=float,
        default=5.0,
        help="Minimum gripper action span used to flag manipulation candidates.",
    )
    args = parser.parse_args()

    frames = load_frames(args.dataset_root)
    candidates: list[int] = []

    print("EPISODE MOTION SUMMARY")
    for episode_id, episode in frames.groupby("episode_index"):
        episode = episode.sort_values("frame_index")
        action = np.stack(episode["action"].apply(np.asarray))
        if action.ndim != 2 or action.shape[1] != len(JOINT_NAMES):
            raise SystemExit(f"Episode {episode_id} has unexpected action shape {action.shape}")

        movement = np.abs(np.diff(action, axis=0)).sum() if len(action) > 1 else 0.0
        spans = action.max(axis=0) - action.min(axis=0)
        gripper_span = float(spans[-1])
        if gripper_span >= args.candidate_gripper_span:
            candidates.append(int(episode_id))

        print("\n" + "=" * 72)
        print(f"EPISODE {int(episode_id)} | frames={len(episode)} | total_motion={movement:.2f}")
        for index, name in enumerate(JOINT_NAMES):
            print(
                f"{name:16s} "
                f"min={action[:, index].min():8.2f} "
                f"max={action[:, index].max():8.2f} "
                f"span={spans[index]:8.2f}"
            )
        print(
            f"GRIPPER start={action[0, -1]:.2f} "
            f"min={action[:, -1].min():.2f} "
            f"max={action[:, -1].max():.2f} "
            f"end={action[-1, -1]:.2f}"
        )

    print("\nMANIPULATION_CANDIDATES_BY_GRIPPER_SPAN =", candidates)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
