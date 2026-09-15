# Final Demo Script

Target length: 2 to 3 minutes. Keep the hardware result and software fallback clearly separated. Tenki is an optional supporting proof; it must never displace the Intel/Gatekeeper physical story.

## 0:00-0:20 — Open with the sponsor and authority story

> We're building on Intel's Physical AI stack because the governance problem appears when perception and robotics get fast enough to close the loop. Intel gives the system machine-speed capability. Gatekeeper adds the independent boundary that decides whether that exact capability is authorized to become physical action now. We are not checking a rule after the fact; we are constraining which state transitions are executable at all.

Show the architecture path, OpenVINO/runtime evidence and effective authority mode. If Tenki is live, show it as a separate **derived-evidence** plane with `authority=false`, not as another authority box.

If using the technical slide, point to the five-stage summary:

```text
Observe -> Propose -> Project into the admissible state space -> Execute -> Prove
```

If Tenki is enabled, the implementation inserts a bounded `Derive evidence` step between Propose and Project without changing the authority invariant.

## 0:20-0:55 — Intel inference, normal object

Show the live frame and normalized evidence. Name the actual Intel component visible in the trace.

> This frame is processed through the Intel inference path. The detector sees a normal object and the planner proposes the accept path, but that proposal has no authority by itself. The inference result becomes evidence. Gatekeeper evaluates the exact evidence and exact action before anything reaches the robot.

If live Tenki has passed its non-actuating probe, show the Tenki `artifact_ref` and `claim_hash` before the Gatekeeper verdict:

> We also send a hash-bound representation of this exact proposal through Tenki as isolated compute. Tenki returns derived evidence only. Notice the contract says `authority=false`. That evidence can accompany the request, but Tenki cannot authorize the robot. Gatekeeper remains the sole execution authority.

Do not include this paragraph if the current Tenki endpoint has not been verified. Never substitute historical Tenki evidence for the current run.

Run the action. Show ALLOW, dispatch and the post-action verification.

> Intel handles the physical-AI capability. Gatekeeper establishes that this transition remains admissible. We record the decision before execution, then independently record the observed result afterward.

## 0:55-1:20 — Anomaly evidence, defective object

Place/show the visibly defective object. If the trained Anomalib workflow is live, show its score and localization on screen and name it explicitly.

> Now the perception evidence changes. The anomaly result is a fact, not automatically a violation. The planner proposes the reject path, and the same authority boundary asks whether that transition remains admissible under the current evidence.

Run the action. Show reject placement and post-action evidence.

> Perception supplies facts. Authority determines admissibility.

If the trained Anomalib workflow is not yet verified, say so and use the reference-detector trace rather than claiming it.

## 1:20-1:45 — TRANSFORM

Present an overspeed proposal.

> The physical-AI stack is capable of issuing this proposal, but capability is not authority. This command is outside the permitted movement envelope. Gatekeeper projects it into the admissible action space and returns TRANSFORM with the exact constrained action that may enter the robotics execution path.

If Tenki is enabled, be precise: its claim is bound to the original proposal. Gatekeeper owns the transformed replacement.

Show proposed speed, authorized speed and measured execution speed. Emphasize that the original overspeed action never reaches the actuator.

## 1:45-2:10 — Stale evidence

Use stale evidence or an intentionally expired frame.

> This is the important failure case. OpenVINO still works. The planner still works. The robot still works. The proposal can still be well formed. The only thing that changed is whether this evidence is current enough for that state transition to remain admissible.

Show HOLD and zero new movement.

> Queued is not authorized.

## 2:10-2:30 — Authority outage

If the live demo permits it, point the adapter at the declared unavailable test endpoint or use the pre-recorded verified outage trace.

> If authority cannot be established, the system fails closed. It does not silently fall back to ungoverned execution.

Show HOLD and no actuator call.

## 2:30-2:55 — Receipts and sponsor close

Show the linked verification view and, if available, the Intel runtime/device/model readout from `scripts/sponsor_showcase.py`.

If Tenki is live, show the receipt order:

```text
PRE_AUTHORITY_EVIDENCE -> AUTHORITY_DECISION -> PHYSICAL_OUTCOME
```

and point out that the Tenki receipt explicitly carries `authority=false`.

> Every physical effect has a before-and-after accountability chain: what Intel's perception path observed, what the model proposed, any declared derived evidence, what was authorized, what entered the robot path and what was observed afterward.

Close:

> Intel makes the physical-AI loop fast enough to matter. Gatekeeper makes machine-speed action governable. Capability proposes. Authority decides.

Credit AI Infra Summit, lablab.ai and Native as the event/hackathon ecosystem separately from the technical sponsor proof. If Tenki is shown, describe it accurately as the isolated derived-compute/evidence plane used by this build; do not call it authority.

## Deeper technical answer if a judge asks

If asked what the mathematics contributes, keep it concise:

> We model authority as an invariant-preserving transition system. The invariant defines an admissible state space. The planner can choose among possibilities, but only transitions that remain in that space may execute. The invariant constrains action; it does not pretend to be the planner.

If asked where Tenki fits:

> Tenki is outside the authority plane. We hash the exact evidence/action artifact, obtain a non-authoritative derived claim, bind that claim into the request and then ask Gatekeeper for authority. Compute can add evidence; it cannot self-authorize effect.

Do not introduce the exploratory whiteboard notation or GOI comparison unless the discussion specifically turns to research methodology. Those are documented in `AUTHORITY_INVARIANT.md` and are not required for the primary pitch.

## Demo recovery rules

If hardware integration becomes unreliable, do not improvise claims. Fall back to the frozen native software rehearsal and explain exactly which pieces are simulated. If production Gatekeeper is unavailable, show the non-actuating contract probe plus the repository reference-authority execution and label them separately. If Tenki is unavailable, use `TENKI_MODE=observe` or `off` unless the declared judged proof specifically requires it; never weaken Gatekeeper or freshness rules to keep Tenki in the path. If a detector or VLA output is incomplete, do not add permissive defaults during the demo. If receipt verification fails, stop the effect path and diagnose rather than bypassing the guard.
