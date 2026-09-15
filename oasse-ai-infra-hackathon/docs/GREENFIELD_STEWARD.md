# Greenfield Steward

The Greenfield Steward is an independently authored, MIT-licensed coordination layer for the AI Infra project. It is designed to manage multiple **non-authoritative pre-execution agents** without moving or weakening the Gatekeeper boundary.

It does not copy the earlier Runtype Steward implementation. The prior project proved the architectural idea; this repository contains a new implementation written against the Physical AI contracts already present here.

## Placement

```text
Intel perception
      |
      v
 EvidenceFrame
      |
      v
VLA / planner
      |
      v
ProposedAction
      |
      v
+---------------------------------------+
| GREENFIELD STEWARD                    |
|                                       |
| binding-review agent                  |
| transition-summary agent              |
| Tenki derived-evidence agent optional |
| future bounded review agents          |
|                                       |
| authority = false                     |
+-------------------+-------------------+
                    |
                    v
              GATEKEEPER
          sole authority source
                    |
                    v
           controlled actuator
```

The Steward coordinates evidence. It never returns ALLOW, TRANSFORM, HOLD or DENY. Gatekeeper remains the only authority source.

## What it manages

The default greenfield roster contains two local deterministic agents:

- `binding-review`: proves that the proposal is still bound to the exact observed evidence and records evidence/action digests.
- `transition-summary`: summarizes the proposed physical transition, including action type, target, speed, trajectory length and observed perception facts. It does not decide whether those facts are allowed.

If `TENKI_MODE` is enabled, the existing Tenki `/derive` provider is wrapped as a third Steward-managed agent named `tenki-derive`.

Additional agents can implement the `StewardAgent` protocol without changing the orchestrator or authority layer.

## Deterministic coordination

Every run creates a deterministic plan from:

- exact physical-action `artifact_ref`;
- requested effect;
- principal;
- sorted agent roster;
- each agent role and required flag.

The plan receives a stable `plan_id`. Agent outputs are normalized, sorted by `agent_id`, hashed without timing data and aggregated into a stable `state_hash`.

Timing is still recorded separately for performance review but cannot alter plan identity or the deterministic state hash.

## Security rules

Every agent receives detached copies of the evidence and proposal. If an agent mutates either copy, its result is rejected.

Agent results must explicitly remain `authority: false`. The Steward rejects any nested attempt to assert:

- authority;
- permit;
- capability token;
- Gatekeeper verdict;
- authorized action;
- verdict.

The Steward itself also returns `authority: false`. It cannot change action identity, speed, target, trajectory, actor, object or evidence binding because it plugs into the existing pre-authority evidence seam.

## Modes

The existing Physical AI runtime is unchanged by default.

```sh
STEWARD_MODE=off
```

To run the Greenfield Steward explicitly:

```sh
STEWARD_MODE=observe
TENKI_MODE=off
python scripts/probe_steward.py --output onsite/steward-probe.json
python scripts/run_steward_demo.py
```

To include Tenki as a Steward-managed agent:

```sh
STEWARD_MODE=observe
TENKI_MODE=observe
TENKI_DERIVE_URL=https://.../derive
python scripts/probe_steward.py --output onsite/steward-probe.json
```

For a judged proof where both Steward and Tenki are declared prerequisites:

```sh
STEWARD_MODE=required
TENKI_MODE=required
TENKI_DERIVE_URL=https://.../derive
```

`STEWARD_MIN_SUCCESSES` can set a bounded minimum successful-agent count. If omitted, the Steward requires at least the configured required agents, with a minimum of one successful agent.

## Failure behavior

In observe mode, an optional agent can fail while the Steward returns `DEGRADED`; Gatekeeper still receives the successful bounded evidence.

In required mode, a required-agent failure or unmet quorum raises a bounded Steward failure. The existing orchestrator converts that failure to HOLD before Gatekeeper or the actuator can be called.

A Steward failure is not a Gatekeeper failure. A Tenki failure is not a Steward authority decision. The three planes remain distinct.

## Onsite recommendation

Do not put the Steward into the first robot bring-up path.

Use this order:

1. Intel camera/runtime green.
2. Planner/VLA green.
3. Gatekeeper-to-controller path green.
4. Tenki `/derive` green if used.
5. Run `probe_steward.py` with `STEWARD_MODE=observe`.
6. Measure total pre-authority latency and verify evidence freshness still clears dispatch.
7. Promote to required only if the complete path remains stable inside the measured freshness budget.

The pitch should remain simple:

> Intel supplies capability. The Steward coordinates non-authoritative agents. Tenki supplies isolated derived compute. Gatekeeper alone authorizes physical effect.
