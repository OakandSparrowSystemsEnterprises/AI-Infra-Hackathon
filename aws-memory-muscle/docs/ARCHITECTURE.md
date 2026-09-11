# Architecture

## Runtime shape

```text
RocketRide operator/chat
        |
        v
RocketRide coding agent
   |        |        |
   v        v        v
Cognee   HydraDB   Hotdata
learned  durable   live state
memory   graph     / analytics
        \    |    /
         \   |   /
          v  v  v
        diagnosis / plan
              |
              v
        Tenki sandbox
      clone / edit / test
              |
              v
            Snyk
       security evidence
              |
              v
       Action Envelope
              |
              v
   external Gatekeeper V2
 ALLOW / TRANSFORM / HOLD / DENY
              |
      authorized effect only
              |
              v
      controlled GitHub effect
              |
              v
 Learning Event → Cognee + HydraDB
 successful procedure → Rote
```

## Authority boundary

Sponsor systems are evidence, memory, orchestration, analytics, execution, or reliability planes. They are non-authoritative. A successful prior run, a Rote Play, a Cognee recall, a Hydra relationship, a Hotdata query, a Tenki test pass, a Snyk scan, or a RocketRide decision does not grant execution authority.

Only Gatekeeper can issue the authority verdict. The effect adapter must reject HOLD and DENY, reject stale or mismatched action digests, and fail closed when the authority service is unavailable or malformed.

## Credential boundary

The Tenki sandbox should not receive an unrestricted credential capable of directly modifying the authoritative repository. Tenki may clone/read a demo repository and produce candidate changes. The controlled effect happens outside the sandbox after Gatekeeper authorization.

## Memory split

Cognee owns semantic memory construction: what was learned and how it should be recalled.

HydraDB owns durable connected state: failure, component, remediation, test, evidence, receipt, and outcome relationships across runs.

Hotdata owns live state: current test failures, CI status, coverage, changed files, scan findings, timing, and other run-scoped analytical facts.

Rote owns procedure memory: the successful method, replayed with fresh inputs and a fresh authority check.

## Runtype / V2-NPU inheritance

The system inherits the proven separation that work may move through external infrastructure while authority does not. Workers and sponsor planes may supply evidence and outputs but cannot manufacture capabilities, permits, or authorization.
