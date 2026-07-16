"""AI remediation-advisor endpoints.

Lets the frontend pick a past scan, list its (deduplicated) vulnerabilities, and
get an LLM-generated "bilan" (analysis + fix) for each one.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from beanie import PydanticObjectId

import datetime

from app.models.target import Target
from app.models.scan_result import ScanResult
from app.models.ai_conversation import AiConversation, AiMessage
from app.core import ai_helper

router = APIRouter()


class ExplainRequest(BaseModel):
    target_id: str
    title: str
    description: str = ""
    severity: str = ""


class AskRequest(BaseModel):
    target_id: str
    title: str
    question: str


@router.get("/status")
async def ai_status():
    """Whether the LLM advisor is configured (has an API key)."""
    return {"configured": ai_helper.is_configured(), "model": ai_helper.NVIDIA_MODEL}


@router.get("/scans")
async def ai_scans():
    """List past scans that have at least one vulnerability (for the AI tab picker)."""
    results = await ScanResult.find_all().sort(-ScanResult.created_at).to_list()
    seen = set()
    scans = []
    for r in results:
        if r.target_id in seen:
            continue
        if not r.vulnerabilities:
            continue
        seen.add(r.target_id)
        target = None
        try:
            target = await Target.get(PydanticObjectId(r.target_id))
        except Exception:
            pass
        scans.append({
            "target_id": r.target_id,
            "target_value": target.value if target else r.target_id,
            "target_type": target.targetType if target else "?",
            "vuln_count": len(r.vulnerabilities),
            "created_at": r.created_at.isoformat(),
        })
    return {"scans": scans, "total": len(scans)}


@router.get("/scan/{target_id}/vulnerabilities")
async def ai_scan_vulns(target_id: str):
    """Return the deduplicated vulnerabilities of a scan (grouped by title)."""
    results = await ScanResult.find(ScanResult.target_id == target_id).sort(-ScanResult.created_at).to_list()
    if not results:
        raise HTTPException(status_code=404, detail="No scan found for this target")

    grouped: dict = {}
    for r in results:
        for v in r.vulnerabilities:
            key = v.title
            if key not in grouped:
                grouped[key] = {
                    "title": v.title,
                    "description": v.description or "",
                    "severity": v.severity or "info",
                    "count": 0,
                }
            grouped[key]["count"] += 1

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    vulns = sorted(grouped.values(), key=lambda x: order.get((x["severity"] or "info").lower(), 5))
    return {"vulnerabilities": vulns, "unique": len(vulns)}


async def _get_conversation(target_id: str, title: str):
    return await AiConversation.find_one(
        AiConversation.target_id == target_id,
        AiConversation.vuln_title == title,
    )


@router.get("/conversation/{target_id}")
async def ai_conversation(target_id: str, title: str):
    """Return the stored bilan + Q&A history for one vulnerability (no LLM call)."""
    convo = await _get_conversation(target_id, title)
    if not convo:
        return {"exists": False, "bilan": None, "messages": []}
    return {
        "exists": True,
        "bilan": convo.bilan,
        "messages": [{"role": m.role, "content": m.content, "ts": m.ts.isoformat()} for m in convo.messages],
    }


@router.post("/explain")
async def ai_explain(req: ExplainRequest):
    """Get the LLM bilan for ONE vulnerability of ONE scan.

    Persisted in MongoDB per (target_id, title): the model is only ever billed
    once per vulnerability per scan — later calls replay the stored bilan.
    """
    convo = await _get_conversation(req.target_id, req.title)
    if convo and convo.bilan:
        return {**convo.bilan, "cached": True}

    if not ai_helper.is_configured():
        raise HTTPException(status_code=503, detail="AI advisor not configured (missing NVIDIA_API_KEY).")

    bilan = await ai_helper.explain_vulnerability(
        title=req.title, description=req.description, severity=req.severity
    )

    # Never persist a failed call (rate limit, network, bad response) — otherwise
    # the error would be replayed forever and the vuln could never be analysed.
    if bilan.get("error"):
        raise HTTPException(status_code=503, detail=bilan.get("analysis", "AI request failed."))

    if convo:
        convo.bilan = bilan
        convo.updated_at = datetime.datetime.utcnow()
        await convo.save()
    else:
        await AiConversation(
            target_id=req.target_id,
            vuln_title=req.title,
            severity=req.severity,
            bilan=bilan,
        ).insert()

    return {**bilan, "cached": False}


@router.post("/ask")
async def ai_ask(req: AskRequest):
    """Ask a follow-up question about a vulnerability. History is persisted."""
    if not ai_helper.is_configured():
        raise HTTPException(status_code=503, detail="AI advisor not configured (missing NVIDIA_API_KEY).")

    convo = await _get_conversation(req.target_id, req.title)
    if not convo:
        raise HTTPException(status_code=404, detail="Analyse this vulnerability first.")

    history = [{"role": m.role, "content": m.content} for m in convo.messages]
    answer = await ai_helper.ask_followup(
        title=req.title,
        severity=convo.severity or (convo.bilan or {}).get("severity", ""),
        bilan=convo.bilan or {},
        history=history,
        question=req.question,
    )

    convo.messages.append(AiMessage(role="user", content=req.question))
    convo.messages.append(AiMessage(role="assistant", content=answer))
    convo.updated_at = datetime.datetime.utcnow()
    await convo.save()

    return {"answer": answer, "messages": [
        {"role": m.role, "content": m.content, "ts": m.ts.isoformat()} for m in convo.messages
    ]}
