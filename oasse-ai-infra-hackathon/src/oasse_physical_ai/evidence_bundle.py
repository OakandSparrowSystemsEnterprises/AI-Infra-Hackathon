"""Portable, content-checked rehearsal evidence. Hash integrity is not a signature."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path, PurePosixPath
import re
import struct
import zlib
import zipfile
from typing import Any

from .normalization import integer, text
from .receipts import canonical_json, sha256_hex


def verify_receipts(records: list[dict]) -> str:
    if not isinstance(records, list) or not 1 <= len(records) <= 10000:
        raise ValueError("receipt list must be nonempty and bounded")
    previous = "GENESIS"
    decisions: dict[str, dict] = {}
    outcomes: dict[str, dict] = {}
    ids = set()
    for receipt in records:
        if not isinstance(receipt, dict): raise ValueError("invalid receipt")
        text(receipt["receipt_id"], "receipt_id")
        if receipt["receipt_id"] in ids: raise ValueError("duplicate receipt ID")
        ids.add(receipt["receipt_id"])
        integer(receipt["created_at_ms"], "created_at_ms")
        payload = receipt["payload"]
        if not isinstance(payload, dict): raise ValueError("invalid payload")
        if receipt["prev_hash"] != previous or sha256_hex(canonical_json(payload)) != receipt["payload_hash"]:
            raise ValueError("receipt chain or payload mismatch")
        envelope = {key: receipt[key] for key in ("receipt_id", "receipt_type", "created_at_ms", "payload_hash", "prev_hash")}
        if sha256_hex(canonical_json(envelope)) != receipt["receipt_hash"]:
            raise ValueError("receipt envelope mismatch")
        kind = receipt["receipt_type"]
        if kind == "AUTHORITY_DECISION":
            decisions[receipt["receipt_hash"]] = payload
        elif kind == "PHYSICAL_OUTCOME":
            decision = decisions.get(payload.get("decision_receipt_hash"))
            if not decision or decision["verdict"] not in {"ALLOW", "TRANSFORM"} or not decision.get("authorized_action"):
                raise ValueError("outcome has no prior executable decision")
            if payload.get("decision_id") != decision["decision_id"] or payload.get("authorized_action_id") != decision["authorized_action"]["action_id"]:
                raise ValueError("outcome binding mismatch")
            outcomes[receipt["receipt_hash"]] = payload
        elif kind == "TASK_VERIFICATION":
            decision = decisions.get(payload.get("decision_receipt_hash"))
            if not decision: raise ValueError("task has no prior decision")
            if payload.get("task_complete") is True:
                outcome = outcomes.get(payload.get("outcome_receipt_hash"))
                if not outcome or outcome.get("execution_confirmed") is not True:
                    raise ValueError("completed task has no confirmed outcome")
                if outcome["decision_receipt_hash"] != payload["decision_receipt_hash"]:
                    raise ValueError("task and outcome refer to different decisions")
                verification = payload["verification"]
                observation = verification.get("observation", {})
                authorized = decision["authorized_action"]
                if (payload.get("status") != "COMPLETE" or verification.get("verified") is not True
                    or observation.get("observed_bin") != authorized["target_bin"]
                    or observation.get("object_id") != authorized["object_id"]
                    or observation.get("object_released") is not True):
                    raise ValueError("task completion not supported by postcondition")
        else:
            raise ValueError("unknown receipt kind")
        previous = receipt["receipt_hash"]
    return previous


def verify_record(record: dict) -> None:
    if record.get("schema") != "oasse.inspection-rehearsal.v1":
        raise ValueError("unsupported rehearsal schema")
    cases = record.get("cases")
    if not isinstance(cases, list) or not cases: raise ValueError("no rehearsal cases")
    names = set()
    for case in cases:
        name = case["scenario"]
        if name in names: raise ValueError("duplicate scenario")
        names.add(name)
        verify_receipts(case["receipts"])
        task = case["task"]
        matching = [r for r in case["receipts"] if r["receipt_hash"] == task["task_receipt_hash"]]
        if len(matching) != 1 or matching[0]["receipt_type"] != "TASK_VERIFICATION":
            raise ValueError("task receipt missing")
        payload = matching[0]["payload"]
        if any(task.get(key) != value for key, value in payload.items()):
            raise ValueError("reported task differs from the receipt")
        dispatch = task["dispatch"]
        if dispatch["decision_receipt"] not in case["receipts"]:
            raise ValueError("reported decision receipt missing")
        if dispatch["decision"] != dispatch["decision_receipt"]["payload"]:
            raise ValueError("reported decision differs from sealed payload")
        if dispatch["outcome_receipt"] is not None and dispatch["outcome_receipt"] not in case["receipts"]:
            raise ValueError("reported outcome receipt missing")
        if case["expected_task_complete"] is not task["task_complete"]:
            raise ValueError("scenario expectation failed")


def rgb_png(rgb: bytes, width: int, height: int) -> bytes:
    """Encode captured RGB8 bytes with only the standard library, without edits."""
    if type(width) is not int or type(height) is not int or not 1 <= width <= 2048 or not 1 <= height <= 2048:
        raise ValueError("invalid image shape")
    if type(rgb) is not bytes or len(rgb) != width*height*3: raise ValueError("invalid RGB frame")
    def chunk(kind, body):
        return struct.pack("!I", len(body))+kind+body+struct.pack("!I", zlib.crc32(kind+body)&0xffffffff)
    rows = b"".join(b"\0"+rgb[y*width*3:(y+1)*width*3] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR", struct.pack("!2I5B",width,height,8,2,0,0,0))
            +chunk(b"IDAT",zlib.compress(rows))+chunk(b"IEND",b""))


def _member(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if not isinstance(name, str) or not name or path.is_absolute() or any(p in {"..", ".", ""} for p in name.split("/")) or "\\" in name or ":" in name:
        raise ValueError("unsafe bundle member")
    return path


def judge_html(record: dict) -> str:
    cards = []
    for case in record["cases"]:
        task = case["task"]
        decision = task["dispatch"]["decision"]
        observed = task["verification"].get("observation", {})
        name = html.escape(case["scenario"])
        image = ""
        for field, caption in (("before_image", "Inspection frame"), ("after_image", "Post-execution view")):
            if case.get(field):
                _member(case[field])
                image += f'<figure><img src="{html.escape(case[field], quote=True)}" alt="{caption}"><figcaption>{caption}</figcaption></figure>'
        cards.append(f'<section><h2>{name}</h2><p class="status">{html.escape(task["status"])} / {decision["verdict"]}</p>'
            f'<p>Requested destination: {html.escape(str(task["requested_bin"]))}. Observed destination: {html.escape(str(observed.get("observed_bin", "not verified")))}.</p>'
            f'<p>Dispatch attempted: {task["dispatch_attempted"]}. Task complete: {task["task_complete"]}.</p>'
            f'<p>Physics steps: {case["physics_steps"]}. Receipt head: <code>{task["task_receipt_hash"][:20]}</code></p>'
            f'<div class="frames">{image}</div></section>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Gatekeeper | Inspection Rehearsal</title><style>body{margin:0;background:#111820;color:#e9eef2;font:16px system-ui;line-height:1.55}main{max-width:1100px;margin:auto;padding:36px}h1{font-size:38px;margin:8px 0}header{border-bottom:1px solid #45505a;padding-bottom:24px}.scope{color:#ced7df;max-width:850px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:18px;margin-top:24px}section{background:#1a2530;border:1px solid #384956;border-radius:12px;padding:20px}.status{font-weight:700;font-size:19px}code{word-break:break-all}.frames{display:flex;gap:12px}figure{margin:0;flex:1}img{width:100%;image-rendering:auto}figcaption{font-size:12px;color:#c6d0d8}</style><main><header>'
        '<div>OAK &amp; SPARROW SYSTEMS ENTERPRISE</div><h1>Inspection. Authority. Verified outcome.</h1>'
        '<p class="scope">Native OpenVINO and MuJoCo rehearsal. Scripted planner, reference-image detector, idealized Cartesian suction grip. This is not an SO-101 hardware or trained-model demonstration.</p>'
        f'<p>Source: <code>{html.escape(str(record.get("source_commit", "unrecorded")))}</code>. Read <code>record.json</code> and verify <code>manifest.json</code> for the recorded evidence.</p></header>'
        '<div class="grid">'+"".join(cards)+'</div></main></html>')


def write_bundle(directory: Path, record: dict, attachments: dict[str, bytes] | None = None) -> str:
    verify_record(record)
    directory = Path(directory)
    if directory.exists() and any(directory.iterdir()): raise ValueError("bundle output must be empty")
    directory.mkdir(parents=True, exist_ok=True)
    files = {"record.json": (json.dumps(record,indent=2,allow_nan=False)+"\n").encode(),
             "index.html": judge_html(record).encode()}
    for name, data in (attachments or {}).items():
        _member(name)
        if name in files or name == "manifest.json" or not name.endswith((".png", ".json", ".txt", ".xml", ".bin")):
            raise ValueError("unsupported or reserved attachment")
        if type(data) is not bytes or len(data)>20*1024*1024: raise ValueError("attachment too large")
        files[name] = data
    manifest = {"schema": "oasse.evidence-bundle.v1", "source_commit": record.get("source_commit"),
        "files": {name:{"sha256":hashlib.sha256(data).hexdigest(),"size":len(data)} for name,data in sorted(files.items())},
        "authenticity": "unsigned-integrity-manifest"}
    for name, data in files.items():
        path=directory/str(_member(name)); path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    manifest_bytes=(json.dumps(manifest,indent=2,sort_keys=True)+"\n").encode()
    (directory/"manifest.json").write_bytes(manifest_bytes)
    verify_bundle(directory)
    return hashlib.sha256(manifest_bytes).hexdigest()


def verify_bundle(directory: Path, *, expected_manifest_sha256: str | None = None) -> dict:
    directory = Path(directory)
    manifest_file = directory/"manifest.json"
    if manifest_file.is_symlink() or not manifest_file.is_file() or manifest_file.stat().st_size>1024*1024:
        raise ValueError("invalid manifest file")
    raw=manifest_file.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    if expected_manifest_sha256 is not None and digest!=expected_manifest_sha256:
        raise ValueError("manifest hash differs from the trusted expected value")
    manifest=json.loads(raw)
    if manifest.get("schema")!="oasse.evidence-bundle.v1": raise ValueError("unsupported manifest")
    expected=manifest["files"]
    actual={p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file() or p.is_symlink()}
    if actual!=set(expected)|{"manifest.json"}: raise ValueError("unmanifested or missing files")
    total=0
    for name, item in expected.items():
        rel=_member(name); path=directory/str(rel)
        if any((directory/Path(*rel.parts[:i])).is_symlink() for i in range(1,len(rel.parts)+1)):
            raise ValueError("symlinks are not bundle artifacts")
        size=path.stat().st_size; total+=size
        if size>20*1024*1024 or total>100*1024*1024: raise ValueError("bundle too large")
        if size!=item["size"] or hashlib.sha256(path.read_bytes()).hexdigest()!=item["sha256"]:
            raise ValueError("artifact hash mismatch")
    record=json.loads((directory/"record.json").read_text())
    if record.get("source_commit") != manifest.get("source_commit"): raise ValueError("source binding mismatch")
    verify_record(record)
    return {"verified":True,"manifest_sha256":digest,"files":len(expected),"cases":len(record["cases"])}


def zip_bundle(directory: Path, destination: Path) -> None:
    verify_bundle(directory)
    with zipfile.ZipFile(destination,"x",compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(Path(directory).rglob("*")):
            if path.is_file(): archive.write(path,path.relative_to(directory).as_posix())
