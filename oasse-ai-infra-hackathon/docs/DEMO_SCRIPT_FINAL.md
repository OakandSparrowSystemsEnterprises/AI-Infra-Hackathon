# Final Demo Script

Target length: 2 to 3 minutes. Keep the hardware result and software fallback clearly separated.

## 0:00-0:20 — Open with the sponsor story

> We're building on Intel's Physical AI stack because the interesting governance problem appears when perception and robotics get fast enough to close the loop. Intel gives the system machine-speed capability. Gatekeeper adds the independent boundary that decides whether that exact capability is authorized to become physical action now.

Show the architecture path, OpenVINO/runtime evidence and effective authority mode.

## 0:20-0:50 — Intel inference, normal object

Show the live frame and normalized evidence. Name the actual Intel component visible in the trace.

> This frame is processed through the Intel inference path. The detector sees a normal object and the planner proposes the accept path, but that proposal has no authority by itself. The inference result becomes evidence. Gatekeeper evaluates the exact evidence and exact action before anything reaches the robot.

Run the action. Show ALLOW, dispatch and the post-action verification.

> Intel handles the physical-AI capability. We record the authority decision before execution, then independently record the observed result afterward.

## 0:50-1:15 — Anomaly evidence, defective object

Place/show the visibly defective object. If the trained Anomalib workflow is live, show its score and localization on screen and name it explicitly.

> Now the Intel perception evidence changes. The anomaly result identifies the defect, and the planner proposes the reject path. The same independent authority boundary evaluates that new proposal against that new evidence.

Run the action. Show reject placement and post-action evidence.

If the trained Anomalib workflow is not yet verified, say so and use the reference-detector trace rather than claiming it.

## 1:15-1:40 — TRANSFORM

Present an overspeed proposal.

> The physical-AI stack is capable of issuing this proposal, but capability is not authority. This command is outside the permitted movement envelope. Gatekeeper returns TRANSFORM with the exact constrained action that may enter the robotics execution path.

Show proposed speed, authorized speed and measured execution speed. Emphasize that the original overspeed action never reaches the actuator.

## 1:40-2:05 — Stale evidence

Use stale evidence or an intentionally expired frame.

> This is the important failure case. OpenVINO still works. The planner still works. The robot still works. The only thing that changed is whether this evidence is current enough to justify physical action.

Show HOLD and zero new movement.

> Queued is not authorized.

## 2:05-2:25 — Authority outage

If the live demo permits it, point the adapter at the declared unavailable test endpoint or use the pre-recorded verified outage trace.

> If authority cannot be established, the system fails closed. It does not silently fall back to ungoverned execution.

Show HOLD and no actuator call.

## 2:25-2:45 — Receipts and sponsor close

Show the linked decision/outcome verification view and, if available, the Intel runtime/device/model readout from `scripts/sponsor_showcase.py`.

> Every physical effect has a before-and-after accountability chain: what Intel's perception path observed, what the model proposed, what was authorized, what entered the robot path and what was observed afterward.

Close:

> Intel makes the physical-AI loop fast enough to matter. Gatekeeper makes machine-speed action governable. Capability proposes. Authority decides.

Credit AI Infra Summit, lablab.ai and Native as the event/hackathon ecosystem separately from the technical sponsor proof.

## Demo recovery rules

If hardware integration becomes unreliable, do not improvise claims. Fall back to the frozen native software rehearsal and explain exactly which pieces are simulated. If production Gatekeeper is unavailable, show the non-actuating contract probe plus the repository reference-authority execution and label them separately. If a detector or VLA output is incomplete, do not add permissive defaults during the demo. If receipt verification fails, stop the effect path and diagnose rather than bypassing the guard.
