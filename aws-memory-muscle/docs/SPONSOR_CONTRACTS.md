# Sponsor Contracts

RocketRide is the application control plane and judge-visible orchestration surface. It owns the agent loop and calls the other planes.

Cognee receives semantic learning events and supports cross-run recall. It must perform real remember and recall work during the demo.

HydraDB receives durable entity/relationship state derived from learning events and returns connected context during a later run. It must be queried during the demo, not only written.

Hotdata receives live repository/run facts and answers current-state questions. It is not the durable memory store.

Tenki is the isolated execution workbench. It performs clone/checkout, edits, tests, and diff generation. It is optional with respect to Main Track judging but load-bearing in the OASSE architecture if available.

Snyk produces machine-readable security evidence for the candidate change before the consequential effect. The scan result is evidence, not authorization.

Rote captures the successful procedure and replays the method on a later run. Replay must still collect fresh inputs, run fresh checks, and request fresh Gatekeeper authorization.

Gatekeeper is preexisting external OASSE technology. It is not a sponsor and is not part of this repository. It remains the sole authority source.
