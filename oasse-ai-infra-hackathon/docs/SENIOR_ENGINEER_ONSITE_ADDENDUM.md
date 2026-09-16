# Senior Engineer Onsite Addendum

This addendum updates the evidence/claim state of `SENIOR_ENGINEER_ARCHITECTURE.md` after the September 15, 2026 Intel onsite session. The underlying authority architecture, trust boundaries, contracts, failure semantics and invariant model remain the architectural baseline; pre-onsite sponsor-status labels in that document should not be read as the current evidence state.

## Current evidence state

| Surface | Current state |
| --- | --- |
| Intel XPU learned-policy path | **Verified onsite**: ACT training/inference on Intel Arc B390 through PyTorch XPU |
| LeRobot / SO-101 control | **Verified onsite**: LeRobot 0.6.1, real follower actuation and encoder readback |
| Pre-execution authority boundary | **Verified onsite with repository reference engine**: HTTP `ReferenceAuthorityEngine`, not production Gatekeeper |
| DENY / no physical handoff | **Verified onsite**: `WORKSPACE_OCCUPIED`, no authorized action, no dispatch |
| ALLOW / exact action binding | **Verified onsite**: `POLICY_SATISFIED`, exact SHA-bound joint command preserved |
| Learned-policy physical outcome | **Verified onsite**: one ACT-generated step reached `PHYSICALLY_VERIFIED` |
| OpenVINO runtime | **Verified onsite for runtime/integration bring-up**: OpenVINO 2026.3 |
| Anomalib / MVTec PaDiM artifact | Runtime/integration bring-up only; **not** a LEGO detector claim |
| Physical AI Studio | Event workflow/ecosystem context; do not infer autonomous-task completion from package/tool presence |
| Robotics AI Suite | Not independently verified in the final physical path |
| Full autonomous LEGO pick/drop | **Pending** |
| Production Gatekeeper | **Not verified onsite** |
| Live Tenki runtime | **Not verified in the final physical path** |
| Physical safe interruption / braking guarantee | **Not verified** |

## Dataset/model correction

The original ten-episode imitation dataset mixed idle and manipulation data. Offline action analysis showed the strongest manipulation/gripper signal in episodes `5,6,8,9`. The first ACT model converged to a hold attractor; clean-v2 retraining therefore uses only `5,6,8,9` with a shorter action-consumption horizon (`n_action_steps=20`).

This is a model/data-quality correction. It does not change the authority contract.

## Closed-loop result

A governed physical rollout completed 600 individually evaluated ALLOW steps through the authority/dispatch path and reached `MAX_STEPS_REACHED`. The run did **not** complete the LEGO task. Treat it as authority/execution-path endurance evidence only.

## Review order

For the current system state, read in this order:

1. `ONSITE_ACT_LEGO.md`
2. `ONSITE_EVIDENCE.md`
3. this addendum
4. `SENIOR_ENGINEER_ARCHITECTURE.md` for the deeper architecture/trust-boundary review

The current claim boundary is deliberately narrower than the target architecture: a learned physical action was governed and verified; autonomous task completion and production-service claims remain separately pending.
