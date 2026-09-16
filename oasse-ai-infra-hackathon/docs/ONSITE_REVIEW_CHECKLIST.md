# Onsite ACT/SO-101 Review Checklist

This checklist is for the next operator/reviewer before any additional physical run.

- Use stable SO-101 serial-by-id paths; do not rely on `/dev/ttyACM*` numbering.
- Confirm the follower calibration ID matches the physical left 12 V arm.
- Confirm the ACT checkpoint was trained on the intended episode subset.
- Run `scripts/check_act_checkpoint.py` against the checkpoint before actuation.
- Run `scripts/analyze_lerobot_dataset.py` against the local dataset when the recording set changes.
- Start the HTTP authority service and verify `/health` reports the expected authority mode.
- For onsite reference-engine runs, describe it as `ReferenceAuthorityEngine`, not production Gatekeeper.
- Verify the camera source before running the policy; camera device numbering can change after reconnects.
- Use `--workspace-clear` and `--execute` only when the physical workspace is actually clear.
- Treat `MAX_STEPS_REACHED` as an incomplete task run, not success.
- Treat `OPERATOR_ABORT` as an abort, not success.
- Preserve proof JSON locally and record hashes in `docs/ONSITE_EVIDENCE.md`; do not commit raw datasets, model weights, calibration state, camera frames, or credentials.
- A full autonomous LEGO claim requires visible task completion plus the corresponding governed proof/evidence record.
