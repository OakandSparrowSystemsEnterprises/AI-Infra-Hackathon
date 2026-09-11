# Infrastructure Contract

## Default deployment decision

Do not self-host sponsor infrastructure during the hackathon unless a managed service is unavailable and the sponsor explicitly recommends the fallback. The default is managed RocketRide, managed Cognee, managed HydraDB, managed Hotdata, one Tenki sandbox, Snyk and Rote inside the sandbox where practical, and Gatekeeper as an external preexisting OASSE authority service.

## Control and data planes

RocketRide is the hackathon control plane. It coordinates the coding-agent flow but does not become authority.

Cognee, HydraDB, and Hotdata are supporting state planes. None may replace or write the Gatekeeper authoritative journal. Sponsor memory, analytics, telemetry, and graph data are evidence or context only.

Tenki is bounded compute. A Tenki worker may produce a candidate patch, tests, logs, and evidence. It must not hold an unrestricted credential that can perform the final governed GitHub effect.

Gatekeeper preserves its existing single-authority semantics. The authoritative journal remains single-writer. Do not point multiple Gatekeeper authorities at one SQLite journal or move authority state into a sponsor database during the hackathon.

The GitHub effect executor is separate from Tenki and is reachable only after an executable Gatekeeper decision is validated against the exact Action Envelope.

## Probe discipline

Run one readiness probe per sponsor at startup and share/cache the result. Do not let multiple concurrent paths independently hammer the same sponsor credentials. Prior agent-native testing showed duplicated concurrent probes can turn a healthy support plane into a presentation failure.

## Failure behavior

A sponsor failure must be explicit and attributable. It must not silently convert to permission. If required evidence is unavailable, the governed effect remains non-executable. Gatekeeper authority health is reported separately from sponsor-plane health so a support-plane regression cannot be mislabeled as an authority failure.

## Telemetry

Operational telemetry is non-authoritative. It may be stored in Hotdata or other sponsor surfaces, but logs, traces, charts, and analytics must never be represented as Gatekeeper receipts or authority decisions.
