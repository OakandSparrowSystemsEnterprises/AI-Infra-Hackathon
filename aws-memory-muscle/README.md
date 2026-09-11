# OASSE AWS Hackathon: Memory to Muscle Memory

This directory is the pre-event skeleton for the September 11, 2026 AWS Data & AI Hackathon at AWS Builder Loft.

The selected Main Track concept is an AI coding agent with durable memory and governed execution. RocketRide is the control plane. Cognee constructs semantic memory. HydraDB stores durable connected state. Hotdata carries live run-scoped repository state. Tenki is the isolated execution workbench. Snyk produces security evidence. Rote captures successful procedure as muscle memory. Gatekeeper remains the external pre-execution authority and is not part of this repository.

The invariant is simple: memory can recommend a known procedure, but memory never grants authority. A consequential effect may occur only after a fresh Gatekeeper decision binds the exact proposed action.

This pre-event tree contains contracts, configuration surfaces, acceptance tests, architecture, and adapter seams. It intentionally contains no functional RocketRide pipeline, no sponsor API implementation, no Tenki remediation workflow, no Rote Play, no hackathon-specific coding logic, and no GitHub actuator. Those are event-created work.

## Local skeleton check

```bash
cd aws-memory-muscle
python -m pip install -e ".[dev]"
pytest
python scripts/check_skeleton.py
```

`EVENT_BUILD_OPEN` defaults closed. Set it to `1` only after the organizer starts the build period.

## Event-created entry points

Create the real RocketRide `.pipe` under `rocketride/` during the build period. Implement sponsor adapters under `src/oasse_memory_muscle/adapters/`. Implement the governed effect path only after Gatekeeper is wired as an external authority service.
