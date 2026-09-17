# OASSE Dark Factory Lite

This directory is the lightweight WeAreDevelopers x BAND hackathon build. BAND is the collaboration layer. Gatekeeper remains an external OASSE authority service behind a narrow HTTP boundary.

The finish-line loop is deliberately small: **Planner → Builder → Reviewer → authority decision**. Planner and Reviewer run Codex read-only. Builder alone receives workspace-write access. Only Reviewer can call the release-authority tool.

The authority request binds the proposed release to a deterministic workspace digest and test evidence. A configured but unreachable Gatekeeper returns HOLD. When no Gatekeeper URL is configured, the app uses an explicitly labeled local reference decision so the BAND workflow can be demonstrated without representing it as production Gatekeeper.

The parent repository is MIT licensed. No Gatekeeper production/runtime source, private policy corpus, credentials, or proprietary OASSE internals belong in this directory.

## First run

Use Node 22.14 or newer, pnpm, and the Codex CLI.

~~~bash
cd wearedevelopers-dark-factory
pnpm install
cp .env.example .env
pnpm doctor
pnpm start
~~~

The BAND-side setup is documented in [BAND_SETUP.md](./BAND_SETUP.md). Create three Remote/External agents named Planner, Builder, and Reviewer, save their one-time API keys and Agent UUIDs into .env, put all three in one BAND room, and give the first small task to @Planner.

For a live authority boundary, set GATEKEEPER_URL, GATEKEEPER_TOKEN, and optionally GATEKEEPER_PATH. The default path is /v1/evaluate. The adapter posts an evidence object and an action object and expects a verdict compatible with ALLOW, TRANSFORM, HOLD, or DENY.

Decision records are written under .dark-factory/receipts/ and are excluded from source control.

## Scope

This is not intended to prove the entire Gatekeeper architecture. It is the minimum working software factory needed to finish the BAND track cleanly while preserving the OASSE IP boundary.
