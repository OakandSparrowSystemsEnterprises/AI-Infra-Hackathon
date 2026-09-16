# Final Demo Script

Target length: 2 to 3 minutes. This script reflects the **verified onsite state**. Do not substitute an unverified autonomous sort or production-service claim.

## 0:00-0:20 — Capability versus authority

> Intel gives the robot machine-speed physical-AI capability. Our ACT policy can propose a real movement and the SO-101 can execute it. Gatekeeper adds a separate question immediately before effect: is this exact action, from this exact evidence, authorized now?

Show the compact path:

```text
camera + robot state
    -> trained ACT proposal
    -> bounded exact joint command
    -> pre-execution authority
    -> physical dispatch
    -> encoder-observed result
```

If using the invariant slide:

```text
Observe -> Propose -> Project into the admissible state space -> Execute -> Prove
```

## 0:20-0:50 — Intel learned-policy proof

Show the runtime facts:

- Intel Arc B390 / PyTorch XPU;
- LeRobot 0.6.1 ACT policy;
- real SO-101 follower;
- OpenVINO 2026.3 runtime evidence separately.

> This is not a scripted robot move. A trained ACT checkpoint produced a six-joint proposal from real state and camera input. Before the command can reach the arm, we bound it and hash-bind the exact command to its evidence and action identities.

Do not describe the MVTec PaDiM bring-up artifact as a LEGO detector.

## 0:50-1:15 — DENY means no physical handoff

Show or replay the occupied-workspace proof:

```text
workspace_clear = false
verdict = DENY
reason = WORKSPACE_OCCUPIED
authorized_action = None
```

> The policy still has capability and the robot is still connected. But no authorized action exists, so there is no physical handoff. Capability does not become authority merely because the model produced a command.

## 1:15-1:50 — ALLOW and exact physical verification

Show the learned-policy physical-step proof:

```text
verdict = ALLOW
reason = POLICY_SATISFIED
status = PHYSICALLY_VERIFIED
```

Show the execution-envelope SHA-256 and at least one before/target/after joint line. If the current hardware setup is stable and the operator approves motion, run the tracked single-step runner; otherwise use the recorded onsite evidence manifest rather than improvising another physical move.

> The authority response preserves the exact bound joint command. Only that authorized command is dispatched. Encoder readback then gives us an observed physical result rather than assuming that a send call means success.

## 1:50-2:15 — Closed-loop path and honest boundary

Show the 600-step governed-run summary:

```text
600 individually authority-approved physical steps
FINAL STATUS = MAX_STEPS_REACHED
```

Then say explicitly:

> That run proves the governed execution path stayed intact for 600 steps. It did not complete the LEGO task, so we do not call it task success.

Explain the dataset finding briefly: the first ten demonstrations contained idle/weak episodes; episodes `5,6,8,9` carry the strongest manipulation/gripper signal and are used for the clean-v2 retrain.

## 2:15-2:40 — Receipts and close

Show `docs/ONSITE_EVIDENCE.md` or the corresponding proof JSON/hash.

> The point is not just that the arm moved. We can show what the model proposed, what authority allowed, the exact command that entered the robot path and what the encoders observed afterward.

Close:

> Intel makes the physical-AI loop capable and fast. Gatekeeper makes the transition from capability to effect governable. Capability proposes. Authority decides.

## If clean-v2 autonomous LEGO succeeds

Promote it only after visible completion and its governed proof are preserved. Add the successful proof hash/video reference to `docs/ONSITE_EVIDENCE.md`, then insert the autonomous pick/drop immediately after the ALLOW section above.

Do not remove the DENY/no-handoff proof; the authority boundary is the core demonstration.

## Claim boundaries during questions

- The onsite authority used the repository `ReferenceAuthorityEngine` behind the HTTP boundary, not production Gatekeeper.
- The trained ACT/SO-101 physical step is verified.
- Full autonomous LEGO pick/drop is pending until a successful governed run is recorded.
- The MVTec PaDiM/OpenVINO artifact is runtime/integration proof, not LEGO-classification proof.
- Robotics AI Suite is not claimed as independently verified in the final physical path.
- Tenki is optional non-authoritative derived evidence. Do not claim a live Tenki run unless a current event probe supports it.

## Recovery rules

If the live arm, camera, checkpoint or authority service is not in the verified state, do not improvise a claim. Use the saved physical proof plus the reproducible software rehearsal. If a detector or policy output is incomplete, do not add permissive defaults. If the authority decision, binding check or encoder verification fails, stop the physical path and diagnose it rather than bypassing the guard.
