from __future__ import annotations

from dataclasses import asdict
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Any, Dict

from .gatekeeper_client import configured_authority_mode, describe_authority
from .models import EvidenceFrame, ProposedAction
from .orchestrator import PhysicalAIOrchestrator

app = FastAPI(title="OASSE Physical AI Authority Demo", version="0.1.0")
orchestrator = PhysicalAIOrchestrator()


class EvaluateRequest(BaseModel):
    evidence: Dict[str, Any]
    action: Dict[str, Any]


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "oasse-physical-ai-authority",
        "authority_boundary": "pre-execution",
        **describe_authority(orchestrator.authority),
        "authority_mode_setting": configured_authority_mode(),
        "receipt_chain_valid": orchestrator.receipts.verify(),
    }


@app.post("/v1/evaluate")
def evaluate(req: EvaluateRequest) -> dict:
    try:
        evidence = EvidenceFrame(**req.evidence)
        action = ProposedAction(**req.action)
    except TypeError as exc:
        raise HTTPException(400, str(exc)) from exc
    return orchestrator.authority.evaluate(evidence, action).to_dict()


@app.post("/v1/demo/{scenario}")
def demo(scenario: str) -> dict:
    allowed = {"allow", "defect", "stale", "occupied", "overspeed", "identity_mismatch", "binding_mismatch", "low_confidence"}
    if scenario not in allowed:
        raise HTTPException(404, f"Unknown scenario: {scenario}")
    return orchestrator.run(scenario).to_dict()


@app.get("/v1/receipts")
def receipts() -> dict:
    return {
        "valid": orchestrator.receipts.verify(),
        "count": len(orchestrator.receipts.all()),
        "head": orchestrator.receipts.head,
        "receipts": [r.to_dict() for r in orchestrator.receipts.all()],
    }


@app.get("/v1/metrics")
def metrics() -> dict:
    return orchestrator.metrics.snapshot()


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return r'''<!doctype html>
<html><head><meta charset="utf-8"><title>Gatekeeper Physical AI</title>
<style>
body{font-family:Inter,system-ui,sans-serif;background:#0c0f12;color:#eef2f5;margin:0;padding:32px}main{max-width:1100px;margin:auto}.eyebrow{letter-spacing:.18em;text-transform:uppercase;color:#b9c0c7;font-size:12px}.hero{border:1px solid #2a3239;border-radius:18px;padding:28px;background:#12171b}.flow{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:28px 0}.node{border:1px solid #343f47;border-radius:12px;padding:14px;text-align:center}.authority{border-width:2px}.buttons{display:flex;flex-wrap:wrap;gap:10px}.buttons button{background:#1c252c;color:#eef2f5;border:1px solid #3e4c55;border-radius:10px;padding:10px 14px;cursor:pointer}pre{white-space:pre-wrap;background:#080a0c;border:1px solid #252c32;border-radius:12px;padding:18px;min-height:220px}.status{font-size:28px;font-weight:700;margin-top:20px}.small{color:#aab4bb}</style></head>
<body><main><div class="hero"><div class="eyebrow">Oak & Sparrow Systems Enterprise · AI Infra Summit 2026</div><h1>Gatekeeper: Pre-Execution Security for Physical AI</h1><p>Capability proposes. Authority decides. Physical execution follows the authority, not the capability.</p>
<p class="small">Default mode runs the MIT-licensed local reference authority engine included in this repository. Set AUTHORITY_MODE=live to route decisions through GatekeeperClient to the production Gatekeeper service, which is not included here. Each decision's policy_version identifies the engine.</p>
<div class="flow"><div class="node">Live Evidence</div><div class="node">Perception</div><div class="node">VLA Proposal</div><div class="node authority">GATEKEEPER<br>ALLOW · TRANSFORM · HOLD · DENY</div><div class="node">Controlled Actuator</div></div>
<div class="buttons">
<button onclick="run('allow')">Fresh / Allow</button><button onclick="run('defect')">Defect / Reject Bin</button><button onclick="run('stale')">Stale / Hold</button><button onclick="run('occupied')">Occupied / Deny</button><button onclick="run('overspeed')">Overspeed / Transform</button><button onclick="run('identity_mismatch')">Wrong Actor / Deny</button><button onclick="run('binding_mismatch')">Evidence Mismatch / Deny</button><button onclick="run('low_confidence')">Low Confidence / Hold</button></div>
<div id="status" class="status">Ready</div><p class="small" id="latency"></p><pre id="out">Run a scenario to produce an authority decision and sealed receipt.</pre></div></main>
<script>
async function run(s){const st=document.getElementById('status');st.textContent='Evaluating…';const r=await fetch('/v1/demo/'+s,{method:'POST'});const j=await r.json();st.textContent=j.decision.verdict+' · '+j.decision.reason_codes.join(', ');document.getElementById('latency').textContent='Authority '+j.decision.authority_latency_ms.toFixed(3)+' ms · total '+j.total_latency_ms.toFixed(3)+' ms · executed '+j.executed;document.getElementById('out').textContent=JSON.stringify(j,null,2);}
</script></body></html>'''
