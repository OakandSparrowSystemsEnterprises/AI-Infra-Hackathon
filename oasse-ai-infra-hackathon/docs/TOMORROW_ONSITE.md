# Historical Pre-Onsite Plan

This file is retained only as the original pre-event integration plan. It is **not** the current operating handoff.

The September 15 onsite session materially advanced the hardware state: the SO-101 leader/follower mapping was corrected, calibration was completed, ACT was trained and run on Intel XPU, the real follower was actuated behind the authority boundary, an explicit DENY/no-handoff case was proven, and one ACT-generated physical action was encoder-verified.

Use these current documents instead:

- [`ONSITE_ACT_LEGO.md`](ONSITE_ACT_LEGO.md) — authoritative onsite hardware/model handoff and clean-v2 procedure.
- [`ONSITE_EVIDENCE.md`](ONSITE_EVIDENCE.md) — compact evidence manifest and proof hashes.
- [`ONSITE_REVIEW_CHECKLIST.md`](ONSITE_REVIEW_CHECKLIST.md) — pre-run reviewer/operator checklist.
- [`ONSITE_SPONSOR_BINDING.md`](ONSITE_SPONSOR_BINDING.md) — sponsor/runtime contract notes where still applicable.

Important changes from the original plan:

- Do not rely on `/dev/ttyACM*` numbering. Use the stable serial-by-id paths recorded in `ONSITE_ACT_LEGO.md`.
- Do not describe the onsite authority as production Gatekeeper; the verified hardware path used the repository `ReferenceAuthorityEngine` behind the HTTP pre-execution boundary.
- Do not describe the MVTec PaDiM bring-up artifact as a LEGO detector.
- Do not treat the 600-step governed rollout as task success; it reached the step budget without completing the LEGO pick/drop.
- The active model work is the clean ACT retrain using episodes `5,6,8,9` with shorter replanning intervals.

This archival file should not be used as a runbook for the next physical session.
