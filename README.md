# AI-Infra-Hackathon

Oak & Sparrow Systems Enterprise LLC entry for the AI Infra Summit 2026 Intel Physical AI Challenge.

camera/sensor evidence → perception → VLA proposed action → Gatekeeper authority evaluation → ALLOW / TRANSFORM / HOLD / DENY → controlled actuator → chained outcome receipt. Gatekeeper independently checks evidence, geometry, freshness, uncertainty, policy, and action state before physical effect.

## Where the application lives

The application is in [`oasse-ai-infra-hackathon/`](oasse-ai-infra-hackathon/). Start with its [README](oasse-ai-infra-hackathon/README.md) for setup and the demo, and [`docs/`](oasse-ai-infra-hackathon/docs/) for architecture, judging, and on-site integration notes.

```bash
cd oasse-ai-infra-hackathon
pip install -e ".[dev]"
python -m pytest tests
python scripts/run_demo.py
```

## License

The code and materials in this repository are licensed under the MIT License. See [`LICENSE`](LICENSE).

This repository is an MIT-licensed integration and demonstration implementation. It does not contain, and its license does not extend to, Oak & Sparrow Systems Enterprise LLC's separate proprietary technology: the Gatekeeper production/runtime source, the proprietary policy corpus, private enterprise integrations, private infrastructure, credentials, patents or patent applications, trade secrets, or any other OASSE technology not distributed here. Gatekeeper is consumed through the `GatekeeperClient` API boundary. The local reference authority engine included here is MIT-licensed repository code and is not the proprietary Gatekeeper production engine. See [`oasse-ai-infra-hackathon/NOTICE.md`](oasse-ai-infra-hackathon/NOTICE.md) for the full boundary statement.
