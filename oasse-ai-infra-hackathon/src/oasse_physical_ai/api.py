from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Any, Dict

from .gatekeeper_client import configured_authority_mode, describe_authority
from .dispatch import validate_inputs
from .models import EvidenceFrame, ProposedAction
from .orchestrator import PhysicalAIOrchestrator, ReceiptIntegrityError
from .dashboard import dashboard_html

app = FastAPI(title="OASSE Physical AI Authority Demo", version="0.2.1")
orchestrator = PhysicalAIOrchestrator()


class EvaluateRequest(BaseModel):
    evidence: Dict[str, Any]
    action: Dict[str, Any]


@app.get("/health")
def health() -> dict:
    valid = orchestrator.receipts.verify()
    return {"status": "ok" if valid else "degraded", "service": "oasse-physical-ai-authority",
            "authority_boundary": "pre-execution", **describe_authority(orchestrator.authority),
            "authority_mode_setting": configured_authority_mode(), "receipt_chain_valid": valid}


@app.post("/v1/evaluate")
def evaluate(req: EvaluateRequest) -> dict:
    try:
        evidence, action = EvidenceFrame(**req.evidence), ProposedAction(**req.action)
        validate_inputs(evidence, action)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise HTTPException(400, "INVALID_EVIDENCE_OR_ACTION") from exc
    try:
        return orchestrator.evaluate_only(evidence, action).to_dict()
    except ReceiptIntegrityError as exc:
        raise HTTPException(503, "RECEIPT_CHAIN_INVALID") from exc


@app.post("/v1/demo/{scenario}")
def demo(scenario: str) -> dict:
    allowed = {"allow", "defect", "stale", "occupied", "overspeed", "identity_mismatch", "binding_mismatch", "low_confidence"}
    if scenario not in allowed:
        raise HTTPException(404, f"Unknown scenario: {scenario}")
    try:
        return orchestrator.run(scenario).to_dict()
    except ReceiptIntegrityError as exc:
        raise HTTPException(503, "RECEIPT_CHAIN_INVALID") from exc


@app.get("/v1/receipts")
def receipts() -> dict:
    with orchestrator._lock:
        records = orchestrator.receipts.all()
        return {"valid": orchestrator.receipts.verify(), "count": len(records),
                "head": orchestrator.receipts.head, "receipts": [r.to_dict() for r in records]}


@app.get("/v1/metrics")
def metrics() -> dict:
    with orchestrator._lock:
        return orchestrator.metrics.snapshot()


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return dashboard_html()
