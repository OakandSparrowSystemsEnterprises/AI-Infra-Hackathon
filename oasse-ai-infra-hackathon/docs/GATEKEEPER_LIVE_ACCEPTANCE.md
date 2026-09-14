# Live Gatekeeper acceptance

The probe uses the existing `GatekeeperClient` contract and `evaluate_only`. It never calls an actuator. Configure the intended HTTPS base endpoint in `GATEKEEPER_URL` and its token in `GATEKEEPER_TOKEN` using local environment or secret storage. Do not put credentials in command arguments, URLs, examples, source files or submission artifacts. Supply the deployed policy version explicitly.

```sh
python scripts/probe_gatekeeper.py --expected-policy-version YOUR_DEPLOYED_POLICY --output /tmp/gatekeeper-probe.json
```

The configured policy must match the declared hackathon fixtures. The tool evaluates a fresh permitted action, an overspeed proposal, stale evidence, occupied workspace, low confidence and mismatched evidence identity. It requires the intended verdicts and exact policy version. For TRANSFORM it checks a genuinely lower speed within the configured ceiling and rejects unrelated physical changes. A local fallback HOLD, an unavailable service, malformed response or mismatched policy cannot make the probe pass. Synthetic fixture evidence is labeled as such.

Service-reported authority latency and client evaluation elapsed time are separate. The latter includes client work and receipt creation and is not advertised as a pure network round trip. HTTP compatibility is not service identity attestation, authenticated signed-receipt verification or an end-to-end physical execution test.

CI covers mock responses and an actual loopback HTTP server. These are not the deployed Gatekeeper service. Loopback and injected-transport reports are explicitly distinguished and cannot satisfy the readiness check for a configured external service. The readiness report requires a complete successful configured HTTPS probe recorded within the preceding day. Its purpose is rehearsal bookkeeping, not cryptographic verification of operator-supplied evidence.

Do not enable hardware based solely on this probe. First confirm the endpoint and policy belong to the intended deployment, reconcile the runtime's exact action representation with the API, run an end-to-end governed simulation against that service, and then retain an operator-supervised physical trace. Keep the original proposal, returned authorized action, actual dispatched bytes and outcome linked. No automatic submission or production deployment is performed by this repository.
