# Gatekeeper: Pre-Execution Security for Physical AI

This repository is the hackathon integration shell for Oak & Sparrow Systems Enterprise LLC's AI Infra Summit 2026 Intel Physical AI Challenge build. It demonstrates one narrow proposition: a model, agent, or robot may possess the technical capability to act without possessing authority to cause the proposed physical state transition.

The demo path is camera/sensor evidence -> perception -> VLA proposal -> Gatekeeper authority evaluation -> ALLOW / TRANSFORM / HOLD / DENY -> controlled actuator -> chained outcome receipt. The authority decision is made before dispatch and is bound to the exact evidence and exact proposed action used for that decision.

## Gatekeeper IP boundary

This repository is an MIT-licensed integration and demonstration implementation. It does not contain Oak & Sparrow's proprietary Gatekeeper production/runtime source or proprietary policy corpus.

Gatekeeper is consumed through the `AuthorityClient` / `GatekeeperClient` API boundary in `src/oasse_physical_ai/gatekeeper_client.py`. `GatekeeperClient` is an MIT-licensed HTTP adapter. The service it is intended to call in the live build is the proprietary Gatekeeper production implementation, which is not contained here.

`ReferenceAuthorityEngine` in `src/oasse_physical_ai/policy.py` is a local, deterministic reference/simulation authority engine. It exists for local simulation, CI, judging rehearsals, and failure testing. It is MIT-licensed repository code. It is not the proprietary Gatekeeper production engine and is not represented as such.

In the live build, set `AUTHORITY_MODE=live` and `GATEKEEPER_URL` (and `GATEKEEPER_TOKEN` if required) to the governed endpoint, and the same orchestrator will call the production authority service through the same boundary. The default, `AUTHORITY_MODE=reference`, uses the local reference engine, and so does any value other than `live` (matched case-insensitively). The `policy_version` field on every decision identifies which engine produced it (`physical-ai-demo-v1` for the reference engine), and `GET /health` reports the effective `authority_mode`.

See [`NOTICE.md`](NOTICE.md) for the full licensing and IP boundary statement.

## Live-mode contract

`GatekeeperClient` posts `{"evidence": ..., "action": ...}` to `GATEKEEPER_URL/v1/evaluate` and expects a JSON object with `decision_id`, `verdict` (`ALLOW`, `TRANSFORM`, `HOLD`, or `DENY`), and optionally `reason_codes`, `evaluated_at_ms`, `authority_latency_ms` (service-reported), `policy_version`, and `authorized_action`.

The adapter fails closed:

- `ALLOW` executes the proposal exactly as submitted. An `ALLOW` that also carries an `authorized_action` differing from the proposal in a physical field is a contradiction and becomes a `HOLD` with `AUTHORIZED_ACTION_CONFLICT`; an unusable or rebound `authorized_action` under `ALLOW` is held with `AUTHORIZED_ACTION_INVALID` or `AUTHORIZED_ACTION_BINDING_MISMATCH` just as under `TRANSFORM`.
- `TRANSFORM` executes only the `authorized_action` returned by Gatekeeper, given as a full action object or just the changed fields, and only if it differs from the proposal in a physical field (`action_type`, `target_bin`, `speed_mps`, `object_id`, or `trajectory`). `metadata` and `requested_at_ms` are never taken from the service; the executed action keeps the proposal's values for both. It never falls back to the original proposal. A `TRANSFORM` with no authorized action, an unusable one (wrong field types, a boolean, negative, or non-finite speed, an empty or malformed trajectory), one that leaves the proposal physically unchanged, or one bound to a different `action_id`, `actor_id`, or `evidence_id` becomes a `HOLD`, with `AUTHORIZED_ACTION_MISSING`, `AUTHORIZED_ACTION_INVALID`, `AUTHORIZED_ACTION_UNCHANGED`, or `AUTHORIZED_ACTION_BINDING_MISMATCH` appended to the service's reason codes.
- Transport errors, timeouts, TLS or proxy problems, and non-2xx statuses become a `HOLD` with `AUTHORITY_UNAVAILABLE` (plus `HTTP_<status>` when a status was received). Bodies that are not JSON, lack `decision_id` or `verdict`, or carry wrongly typed fields become a `HOLD` with `AUTHORITY_RESPONSE_INVALID`. A local evidence or action that cannot be serialized becomes a `HOLD` with `AUTHORITY_REQUEST_INVALID`. `evaluate()` never raises. These decisions carry `policy_version` `gatekeeper-live-unavailable`, record the local time elapsed until the failure as their authority latency (no service-reported value exists), are sealed into the receipt chain like any other decision, and never reach the actuator.

The orchestrator applies the same physical-field rule at the last gate: a `TRANSFORM` whose authorized action is missing or does not physically differ from the proposal is not executed, whichever engine produced it.

`GET /health` reports `authority_mode` (`reference`, `live`, or `custom` for an injected engine, derived from the engine actually wired in), `authority_engine` (its class name), and `authority_mode_setting` (the `AUTHORITY_MODE` value as read). A misconfigured value such as `prod` therefore shows as setting `prod` with effective mode `reference`.

## Run locally

```bash
pip install -e ".[dev]"
python -m pytest tests
python scripts/run_demo.py
uvicorn oasse_physical_ai.api:app --app-dir src --reload
```

Open `http://127.0.0.1:8000/` for the demo console. The API exposes health, scenario execution (evaluation plus governed dispatch), direct evaluation, receipts, and latency metrics.

## Demo thesis

Intel and OpenVINO accelerate the perception and physical-AI execution path. Gatekeeper governs the final transition from proposed action to authorized effect. Performance matters, but speed alone is not the security property. The system must establish whether this actor, using this evidence, for this action, in this environment, at this time, may execute.

The default scenarios are deliberately simple. A fresh, high-confidence clear-workspace action is allowed. Stale evidence is held. Workspace occupancy is denied. A velocity above the configured authority ceiling is transformed into a bounded action. Identity mismatch is denied. An action bound to a different evidence identity is denied. Low-confidence evidence is held. A defective cube is routed to the reject bin and allowed. Every result receives a sealed decision receipt. Executed effects receive a second chained outcome receipt.

## Intel integration boundary

The provider interfaces isolate perception, VLA planning, and actuator control. The current mock providers are runnable without robot hardware. The integration files are prepared for OpenVINO/Physical AI Studio/Robotics AI Suite adapters so the authority semantics remain unchanged when the simulator is replaced by the on-site SO-101 arm and live camera.

## Submission boundary

This is a hackathon integration repository. It is not a production certification, safety certification, legal-compliance certification, or release of the proprietary Gatekeeper authority engine. The demo proves the architecture and records measurable behavior under declared scenarios.

## License

MIT. See [`LICENSE`](LICENSE) (identical to the repository root [`LICENSE`](../LICENSE)) and [`NOTICE.md`](NOTICE.md). The MIT License covers the code and materials actually distributed in this repository. It does not cover OASSE's separate proprietary technology, which is not distributed here.
