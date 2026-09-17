# OASSE Dark Factory Lite

This directory is the lightweight WeAreDevelopers x BAND hackathon build. BAND is the collaboration layer. Gatekeeper remains an external OASSE authority service behind a narrow HTTP boundary.

The finish-line loop is deliberately small: a Planner decomposes work, a Builder implements it, a Reviewer checks the result, and only the Reviewer can request release authority. The authority request binds the proposed release to a workspace digest and test evidence. A configured but unreachable Gatekeeper returns HOLD. When no Gatekeeper URL is configured, the app uses an explicitly labeled local reference decision so the factory can be demonstrated without representing it as production Gatekeeper.

The parent repository is MIT licensed. No Gatekeeper production/runtime source, private policy corpus, credentials, or proprietary OASSE internals belong in this directory.

## Run

Use Node 22.14 or newer and pnpm.

```bash
cd wearedevelopers-dark-factory
pnpm install
cp .env.example .env
```

In BAND Desktop, create three External agents named `Planner`, `Builder`, and `Reviewer`. Copy each agent UUID and API key into the matching environment variables.

Run the three processes in separate terminals:

```bash
pnpm planner
pnpm builder
pnpm reviewer
```

Add all three agents to one BAND room. Give the Planner a small repository task. The Planner hands the implementation to Builder. Builder changes the workspace and runs tests. Reviewer independently checks the result and, only after tests pass, calls `request_release_authority`.

For a live authority boundary, set `GATEKEEPER_URL`, `GATEKEEPER_TOKEN`, and optionally `GATEKEEPER_PATH`. The default path is `/v1/evaluate`. The adapter posts an `evidence` object and an `action` object and expects a verdict compatible with `ALLOW`, `TRANSFORM`, `HOLD`, or `DENY`.

Decision records are written under `.dark-factory/receipts/` and are excluded from source control.

## Scope

This is not intended to prove the entire Gatekeeper architecture. It is the minimum working software factory needed to finish the BAND track cleanly while preserving the OASSE IP boundary.
