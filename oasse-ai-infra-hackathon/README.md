# Gatekeeper: Pre-Execution Security for Physical AI

This repository is the hackathon integration shell for Oak & Sparrow Systems Enterprise's AI Infra Summit 2026 Intel Physical AI Challenge build. It demonstrates one narrow proposition: a model, agent, or robot may possess the technical capability to act without possessing authority to cause the proposed physical state transition.

The demo path is camera/sensor evidence -> perception -> VLA proposal -> Gatekeeper authority evaluation -> ALLOW / TRANSFORM / HOLD / DENY -> controlled actuator -> chained outcome receipt. The authority decision is made before dispatch and is bound to the exact evidence and exact proposed action used for that decision.

The shell intentionally does not contain Oak & Sparrow's proprietary Gatekeeper core or private policy corpus. `GatekeeperClient` is the integration seam. The included deterministic reference authority engine exists for local simulation, CI, judging rehearsals, and failure testing. In the live build, set `GATEKEEPER_URL` to the governed endpoint and the same orchestrator will call the real authority service.

## Run locally

```bash
python scripts/run_demo.py
uvicorn oasse_physical_ai.api:app --app-dir src --reload
```

Open `http://127.0.0.1:8000/` for the demo console. The API exposes health, scenario execution, direct evaluation, dispatch, receipts, and latency metrics.

## Demo thesis

Intel and OpenVINO accelerate the perception and physical-AI execution path. Gatekeeper governs the final transition from proposed action to authorized effect. Performance matters, but speed alone is not the security property. The system must establish whether this actor, using this evidence, for this action, in this environment, at this time, may execute.

The default scenarios are deliberately simple. A fresh, high-confidence clear-workspace action is allowed. Stale evidence is held. Workspace occupancy is denied. A velocity above the configured authority ceiling is transformed into a bounded action. Identity mismatch is denied. Low-confidence evidence is held. Every result receives a sealed decision receipt. Executed effects receive a second chained outcome receipt.

## Intel integration boundary

The provider interfaces isolate perception, VLA planning, and actuator control. The current mock providers are runnable without robot hardware. The integration files are prepared for OpenVINO/Physical AI Studio/Robotics AI Suite adapters so the authority semantics remain unchanged when the simulator is replaced by the on-site SO-101 arm and live camera.

## Submission boundary

This is a hackathon integration repository. It is not a production certification, safety certification, legal-compliance certification, or release of the proprietary Gatekeeper authority engine. The demo proves the architecture and records measurable behavior under declared scenarios.
