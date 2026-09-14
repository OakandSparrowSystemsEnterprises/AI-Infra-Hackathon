# Final Demo Script

Target length: 2 to 3 minutes. Keep the hardware result and software fallback clearly separated.

## 0:00-0:20 — Open

> Physical AI is getting very good at deciding what it *can* do. We built the missing layer that decides what it is *allowed* to do. Gatekeeper sits between a model's proposed action and the physical effect.

Show the architecture path and the effective authority mode.

## 0:20-0:50 — Normal object

Show the live frame and normalized evidence.

> The detector sees a normal object. The planner proposes the accept path, but that proposal has no authority by itself. Gatekeeper evaluates the exact evidence and exact action before anything reaches the robot.

Run the action. Show ALLOW, dispatch and the post-action verification.

> We record the decision before execution, then independently record the observed result afterward.

## 0:50-1:15 — Defective object

Place/show the visibly defective object.

> Now the evidence changes. The planner proposes the reject path. The same authority boundary evaluates that new proposal against that new evidence.

Run the action. Show reject placement and post-action evidence.

## 1:15-1:40 — TRANSFORM

Present an overspeed proposal.

> This proposal is valid in shape but outside the permitted movement envelope. Gatekeeper does not simply say yes or no. It returns TRANSFORM with the exact constrained action that may execute.

Show proposed speed, authorized speed and measured execution speed. Emphasize that the original overspeed action never reaches the actuator.

## 1:40-2:05 — Stale evidence

Use stale evidence or an intentionally expired frame.

> This is the important failure case. The planner still works. The robot still works. The credentials can still be valid. The only thing that changed is whether this evidence is fresh enough to justify the action.

Show HOLD and zero new movement.

> Queued is not authorized.

## 2:05-2:25 — Authority outage

If the live demo permits it, point the adapter at the declared unavailable test endpoint or use the pre-recorded verified outage trace.

> If authority cannot be established, the system fails closed. It does not silently fall back to ungoverned execution.

Show HOLD and no actuator call.

## 2:25-2:45 — Receipts and close

Show the linked decision/outcome verification view.

> Every physical effect has a before-and-after accountability chain: what was observed, what was proposed, what was authorized, what was dispatched and what was observed afterward.

Close:

> Intel makes physical AI faster. Gatekeeper makes machine-speed action governable. Capability proposes. Authority decides.

## Demo recovery rules

If hardware integration becomes unreliable, do not improvise claims. Fall back to the frozen native software rehearsal and explain exactly which pieces are simulated. If production Gatekeeper is unavailable, show the non-actuating contract probe plus the repository reference-authority execution and label them separately. If a detector or VLA output is incomplete, do not add permissive defaults during the demo. If receipt verification fails, stop the effect path and diagnose rather than bypassing the guard.
