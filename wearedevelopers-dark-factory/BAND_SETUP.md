# BAND first-run setup

This is the shortest path from the repository to a working BAND room.

## Create the three BAND agents

Open BAND, go to **Agents**, choose **New Agent**, and create three Remote/External Agents with these identities.

| BAND name | Purpose | Local permission |
| --- | --- | --- |
| Planner | Converts the human request into a tiny implementation handoff | Read only |
| Builder | Implements the handoff and runs verification | Workspace write |
| Reviewer | Independently checks the result and requests release authority | Read only |

When BAND creates each agent, copy the API key immediately. BAND only displays that key once. Open the agent settings and copy its Agent UUID as well.

Copy .env.example to .env, then place the three UUID/API-key pairs into the matching PLANNER_, BUILDER_, and REVIEWER_ variables. Do not commit .env.

## Prepare Codex

The BAND Codex adapter uses your local Codex CLI session.

~~~bash
npm install -g @openai/codex
codex login
~~~

From this directory, install the project and run the preflight.

~~~bash
pnpm install
pnpm doctor
~~~

The doctor checks all three BAND identities, the workspace, Codex availability, and whether the Gatekeeper URL is valid if one is configured. It never prints BAND API keys or the Gatekeeper token.

## Start the factory

~~~bash
pnpm start
~~~

That single command starts Planner, Builder, and Reviewer and keeps all three connected to BAND.

In BAND, create one room and add all three agents. Send the first task to **@Planner**. Use something intentionally small for the first connection test, such as asking it to add a one-line status endpoint or a tiny README change in a disposable workspace.

Planner hands the job to Builder and tells Reviewer what matters. Builder performs the edit and verification. Reviewer checks the result independently. Only Reviewer has the custom tool that can request the Gatekeeper release decision.

## Authority mode

With no GATEKEEPER_URL, the factory produces a clearly labeled local reference decision. This exists only so the BAND flow can be completed before the live OASSE endpoint is attached.

When GATEKEEPER_URL is present, the same flow calls Gatekeeper over HTTP. If that configured endpoint is unavailable or returns malformed output, the release decision is **HOLD**. The factory does not silently fall back to the local reference path.

Decision records are written to .dark-factory/receipts/, which is excluded from source control.
