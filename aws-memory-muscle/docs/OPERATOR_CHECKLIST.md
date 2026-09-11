# Operator Checklist

Before the build period, create or verify sponsor accounts, API keys, RocketRide credits, HydraDB tenant readiness, Hotdata workspace access, Cognee access, Rote access, Snyk authentication, and Tenki access if used. Do not implement the event application yet.

At build open, set `EVENT_BUILD_OPEN=1`, create the real RocketRide `.pipe`, then follow `EVENT_BUILD_ORDER.md` without widening scope until one complete vertical works.

Use a disposable demo repository or branch. Never place production Gatekeeper source, policy corpus, private customer material, enterprise secrets, or unrestricted GitHub credentials inside sponsor sandboxes.

Before submission, export every required RocketRide `.pipe`, run the full demo twice, preserve exact commit SHAs, capture sponsor evidence, confirm Snyk is green enough for judging, verify the Gatekeeper receipt chain, and make the repository/submission disclosure explicit.
