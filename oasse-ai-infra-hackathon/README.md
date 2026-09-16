# Gatekeeper: Pre-Execution Security for Physical AI

This is Oak & Sparrow Systems Enterprise LLC's AI Infra hackathon integration. A model may be capable of proposing a movement without having authority to cause it. The application keeps evidence, planning, derived compute, authority and execution separate, with a decision receipt before dispatch and an outcome receipt after every attempted effect.

The conceptual model is an invariant-preserving transition system: authority defines the admissible state-transition space rather than merely attaching a rule to a completed plan. See [Authority as an Invariant-Preserving Transition System](docs/AUTHORITY_INVARIANT.md).

## Current runnable paths

The default service runs synthetic perception, a scripted proposal generator, the local reference authority engine and a simulated actuator. It provides a lightweight dashboard and API without requiring OpenVINO, MuJoCo, Tenki or robot hardware.

The native simulation path uses actual MuJoCo dynamics in an independently authored three-axis Cartesian carrier scene. The native vision path adds rendered RGB frames and a real compiled OpenVINO IR graph before authority evaluation and controlled physics execution. Its included graph compares pixels against a reference image; it is not a trained anomaly model. Workspace and geometry context are explicitly labeled simulator ground truth.

An optional Tenki path adds isolated, non-authoritative derived evidence between proposal and Gatekeeper. It is OFF by default, so existing behavior and latency remain unchanged. See [Tenki Integration](docs/TENKI_INTEGRATION.md).

### Onsite ACT + SO-101 hardware path

The Intel onsite integration adds a real SO-101 follower and an ACT imitation-learning policy trained on the event workstation's Intel Arc XPU. The reusable runners are parameterized and live under `scripts/`; raw event-machine proofs, model weights, calibration files, datasets, frames and receipts remain generated/local artifacts.

What was physically demonstrated onsite:

- corrected leader/follower hardware identity and calibration
- real SO-101 teleoperation and encoder readback
- ACT training and inference on Intel Arc B390 through PyTorch XPU
- a fresh learned six-joint action bounded by a deterministic motion envelope
- exact SHA-256 binding of the bounded joint action to evidence/action identities
- `DENY / WORKSPACE_OCCUPIED` with no physical handoff
- `ALLOW / POLICY_SATISFIED` with exact authorized joint-action binding preserved
- one ACT-generated authority-approved physical step with encoder verification and status `PHYSICALLY_VERIFIED`
- a 600-step governed closed-loop execution-path run without an authority/actuator-path collapse

The 600-step run did **not** complete the LEGO manipulation task. Dataset analysis showed the first mixed-data ACT model had learned a hold attractor because several recorded episodes were idle or had little gripper signal. Clean retraining was started from the strongest manipulation episodes `[5,6,8,9]`; full autonomous LEGO pick-and-drop was still pending at handoff.

See [Onsite ACT + SO-101 Handoff](docs/ONSITE_ACT_LEGO.md) and [Onsite Evidence Manifest](docs/ONSITE_EVIDENCE.md). The onsite HTTP authority used `ReferenceAuthorityEngine`; it is not represented as the proprietary production Gatekeeper runtime.

See [Architecture](docs/ARCHITECTURE.md), [Phase 2 runtime](docs/PHASE2_RUNTIME.md), [Phase 3 native perception](docs/PHASE3_NATIVE_PERCEPTION.md), and [Jackson's perception handoff](docs/JACKSON_PERCEPTION.md) for exact boundaries and integration instructions.

## Run the default demo

From `oasse-ai-infra-hackathon`:

```sh
python -m pip install -e ".[dev]"
python -m pytest tests -q
python scripts/run_demo.py
uvicorn oasse_physical_ai.api:app --app-dir src --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. Docker builds from this same application directory. The default Docker image intentionally omits the optional vision and simulation runtimes.

## Run native simulation and vision

```sh
python -m pip install -e ".[dev,simulator,perception]"
python scripts/run_mujoco_demo.py
MUJOCO_GL=osmesa OASSE_NATIVE_CAMERA_TESTS=1 python -m pytest tests -q
MUJOCO_GL=osmesa python scripts/run_native_vision_demo.py --output native-vision.json --artifacts-dir demo-output/native-vision
```

Headless Ubuntu needs the `libosmesa6` system package for the vision example. Select the GL backend before importing MuJoCo. CPU inference and Linux OSMesa are exercised by CI. Other device and renderer configurations require their own verification. The native example saves exact rendered PPM images, exported reference IR fixtures and JSON receipts rather than presenting callbacks as executed native components.

## Authority, Tenki and dispatch

The direct path is:

```text
camera -> perception -> EvidenceFrame -> VLA proposal -> ProposedAction -> Gatekeeper -> authorized action -> actuator -> outcome receipt
```

The optional Tenki path is:

```text
camera -> perception -> EvidenceFrame -> VLA proposal -> ProposedAction
       -> Tenki derived evidence (authority=false)
       -> Gatekeeper -> authorized action -> actuator -> outcome receipt
```

Conceptually, if `I` is the governing invariant and `X_I={x:I(x)=iota}` is the admissible state space, an executable transition must remain inside `X_I`. In compact form, `C_I:X_I -> X_I`. The planner chooses proposals; authority determines whether the exact proposed transition is admissible. This does not imply that the invariant chooses the unique next action.

Tenki does not change that authority model. Its client hashes the exact normalized evidence/action artifact, submits the digest, requested effect and principal to `POST /derive`, validates the returned claim, and attaches it under the reserved `pre_authority_evidence.tenki` metadata field. A valid claim must remain `authority=false`, bind to the exact artifact/effect/principal, identify `compute_plane=tenki` and `role=derived_claim_only`, and provide a bounded claim hash. The planner cannot populate that reserved field itself.

`TENKI_MODE=off` is the default. `observe` records a valid Tenki claim when available but does not make Tenki a dependency. `required` produces HOLD before Gatekeeper when the declared Tenki evidence requirement is not satisfied. A successful or failed Tenki attempt is sealed as `PRE_AUTHORITY_EVIDENCE`; it is never represented as an authority decision.

`ALLOW` permits the unchanged proposal. `TRANSFORM` requires an explicitly authorized physical change, not a metadata-only or timestamp-only edit. `HOLD` and `DENY` never dispatch. The live adapter rejects missing or malformed authorized actions, identity rebinding, contradictory ALLOW payloads and nonfinite or wrongly typed values. Transport failures and malformed responses produce fail-closed decisions rather than allowing the action.

The local dispatcher may remove permission but cannot grant it. It snapshots evidence and proposals, validates returned authority decisions and gives the actuator its own isolated action copy. Evidence freshness is checked before dispatch and after receipt creation. A monotonic lease prevents an unchanged wall clock from extending an already-issued evidence deadline. Reused identities and non-increasing capture sequences are held. Identical pixels in a genuinely new capture are not automatically treated as replay. The native simulator additionally checks freshness and action binding before each physics step.

The `dispatch_attempted` field records invocation of an actuator. `executed` requires an explicit success response, rather than merely a callback returning without raising. Unknown status or exceptions produce an unknown outcome, including possible partial effects. Every attempted dispatch gets an outcome receipt. A blocked command does not invoke the actuator. Receipt data is copied to strict finite JSON and chain appends are synchronized. A corrupted prior chain blocks new effects.

These controls operate within one process with trusted integration components. They are not a sandbox against malicious code with direct access to a robot or simulator. Replay state and receipts remain in memory; restart persistence, source authentication, physical braking and hardware emergency stops are separate requirements.

## Perception is not authority

The default and native scenarios intentionally keep perception and authority separate. A defect/anomaly score is an observation, not itself a denial condition. A planner can use that fact to propose the reject path while Gatekeeper still returns ALLOW because the resulting transition satisfies the declared authority policy.

**Perception supplies facts. Authority determines admissibility.**

## API

`GET /health` reports actual authority mode, engine and configured setting, component class names, version and receipt-chain validity. `POST /v1/evaluate` validates an evidence/action pair and seals an evaluation receipt without dispatching or consuming replay state. `POST /v1/demo/{scenario}` evaluates and conditionally dispatches a declared synthetic scenario. `GET /v1/receipts` and `GET /v1/metrics` expose the in-memory demonstration record. Invalid evidence or action fields receive a client error. A corrupted chain receives an unavailable response on evaluation or dispatch.

The default scenarios cover fresh input, a marked object, stale evidence, occupied workspace, overspeed, unrecognized actor, mismatched evidence and low confidence. The native vision runner additionally exercises changed scenes, future timestamps, replay and authority unavailability. Its marked-object case chooses a reject destination in the proposal and executes a short diagnostic carrier movement, not a demonstrated physical grasp or sorting cycle.

## Live Gatekeeper contract and IP boundary

This repository and its local `ReferenceAuthorityEngine`, `AuthorityClient` and `GatekeeperClient` are MIT-licensed integration code. It does not contain the separate proprietary Gatekeeper production/runtime source or policy corpus. The local reference engine is not represented as production Gatekeeper.

Set `AUTHORITY_MODE=live`, `GATEKEEPER_URL`, and `GATEKEEPER_TOKEN` when required to use the external authority service. The current factory matches `live` case-insensitively; any other setting selects the reference engine and `/health` exposes that setting and effective mode. Verify effective mode before a live demonstration. Native CI's outage transport is a declared test fixture, not proof of production connectivity.

`GatekeeperClient` posts `{"evidence": ..., "action": ...}` to `GATEKEEPER_URL/v1/evaluate`. It requires a known `verdict` and a nonempty `decision_id`, with optional `reason_codes`, `evaluated_at_ms`, `authority_latency_ms`, `policy_version` and `authorized_action`. TRANSFORM requires a full action or explicit field changes. Only accepted physical and identity fields are applied; service metadata and requested timestamps do not replace the proposal's informational fields. Service-reported latency and local failure elapsed time are distinguished in the implementation documentation and must not be passed off as a whole-system benchmark.

Tenki is also external runtime technology. No Tenki platform source or credential is distributed by this repository. Configure `TENKI_MODE`, `TENKI_DERIVE_URL`, `TENKI_TIMEOUT_S`, and optionally `TENKI_DERIVE_TOKEN` locally. Run `python scripts/probe_tenki.py --output onsite/tenki-probe.json` before enabling it in the judged path. The probe never calls Gatekeeper or an actuator.

No source or assets from the external LeRobot tutorial are included. Its workflow informed the interface discussion only. See [NOTICE.md](NOTICE.md) for the licensing and proprietary-technology boundary.

## Verification and submission scope

CI tests the lightweight Python path, reference scenarios, Tenki contract/binding behavior, Docker build and real HTTP startup. Separate jobs require native MuJoCo and native OpenVINO imports, execute their tests and smoke runners, and archive exact dependency versions and verification records. Optional-dependency skips in the lightweight job are not counted as native runtime proof; the native job runs the full stack.

The Tenki tests use a bounded mock transport to prove request binding, non-authority enforcement, failure behavior, receipt ordering and TRANSFORM compatibility. They do **not** claim a live Tenki worker. Live runtime status and latency require the onsite probe.

This is a hackathon integration repository, not a production, safety or legal-compliance certification. The included deterministic vision graph, scripted policy and Cartesian scene are declared fixtures. The onsite hardware path demonstrates real learned-policy SO-101 actuation under the same pre-execution authority boundary, while the final autonomous LEGO task remains separately tracked until it is actually completed.

## License

MIT. See [LICENSE](LICENSE), identical to the repository root [LICENSE](../LICENSE), and [NOTICE.md](NOTICE.md). MIT covers the code and materials distributed here, not OASSE's separate undistributed proprietary technology or external Tenki/Intel runtimes.
