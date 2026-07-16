from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from beanie import PydanticObjectId
from app.models.target import Target
from app.models.scan_result import ScanResult, Vulnerability
from app.models.scan_log import ScanLog
from app.pipelines.url_pipeline import UrlPipeline
from app.pipelines.dns_pipeline import DnsPipeline
from app.pipelines.machine_pipeline import MachinePipeline
from app.core import cache
from app.core import progress as progress_store
import asyncio
import shutil
import time
import uuid

router = APIRouter()

# Keep strong references to running background scan tasks so they aren't
# garbage-collected mid-flight.
_background_tasks: set = set()

class ScanRequest(BaseModel):
    target_id: str

class ScanStartRequest(BaseModel):
    target_id: str
    force: bool = False  # bypass the Redis cache and re-scan live


def _build_pipeline(target_type: str, value: str):
    if target_type == "URL":
        return UrlPipeline(), {"url": value}
    if target_type == "DNS":
        return DnsPipeline(), {"domain": value}
    if target_type in ("IP", "CIDR"):
        return MachinePipeline(), {"ip": value}
    return None, None


async def _persist_and_finish(scan_id, target, target_type, results, from_cache, started, prog):
    """Extract vulns, save ScanResult + ScanLog, and close out progress."""
    vulns_raw = results.get("nuclei_result", {}).get("vulnerabilities", [])
    vulns = [Vulnerability(**v) if isinstance(v, dict) else v for v in vulns_raw]

    await ScanResult(
        toolName="pipeline",
        rawJson=results,
        status="completed",
        vulnerabilities=vulns,
        target_id=str(target.id),
    ).insert()

    metrics = _compute_metrics(results)
    duration_ms = int((time.perf_counter() - started) * 1000)
    await ScanLog(
        target_value=target.value,
        target_type=target_type,
        target_id=str(target.id),
        status="completed",
        subdomains=metrics["subdomains"],
        endpoints=metrics["endpoints"],
        ports=metrics["ports"],
        findings=len(vulns),
        duration_ms=duration_ms,
        cached=from_cache,
    ).insert()

    await prog(
        f"Scan terminé — {metrics['subdomains']} sous-domaine(s), "
        f"{metrics['endpoints']} endpoint(s), {metrics['ports']} port(s), "
        f"{len(vulns)} vulnérabilité(s)",
        "success",
    )
    progress_store.finish(scan_id, "completed", results_count=len(vulns), cached=from_cache)


async def _run_scan_job(scan_id, target, target_type, force):
    started = time.perf_counter()

    async def prog(message, level="info"):
        progress_store.push(scan_id, message, level)

    try:
        # 1. Cache lookup
        results = None
        from_cache = False
        if not force:
            await prog("Vérification du cache…")
            results = await cache.get_cached(target_type, target.value)
            if results is not None:
                from_cache = True
                await prog("Résultat trouvé en cache — retour instantané", "success")

        # 2. Live scan on cache miss
        if results is None:
            pipeline, data = _build_pipeline(target_type, target.value)
            if pipeline is None:
                await prog(f"Type de cible inconnu : {target_type}", "error")
                progress_store.finish(scan_id, "error")
                return
            await prog(f"Lancement du pipeline {target_type} sur {target.value}")
            pipeline.pipeline_build(data)
            results = await pipeline.execute_pipeline(progress=prog)
            await prog("Enregistrement dans le cache…")
            await cache.set_cached(target_type, target.value, results)

        await _persist_and_finish(scan_id, target, target_type, results, from_cache, started, prog)
    except Exception as e:
        progress_store.push(scan_id, f"Erreur durant le scan : {e}", "error")
        progress_store.finish(scan_id, "error")


@router.post("/start")
async def start_scan(request: ScanStartRequest):
    try:
        target = await Target.get(PydanticObjectId(request.target_id))
    except Exception:
        raise HTTPException(status_code=404, detail="Target not found")
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    target_type = target.targetType.upper()
    if _build_pipeline(target_type, target.value)[0] is None:
        raise HTTPException(status_code=400, detail=f"Unknown target type: {target.targetType}")

    scan_id = str(uuid.uuid4())
    progress_store.create(scan_id, target_id=str(target.id))
    progress_store.push(scan_id, f"Scan démarré pour {target.value} ({target_type})")

    # Run the scan in the background; the client streams updates via /progress.
    task = asyncio.create_task(_run_scan_job(scan_id, target, target_type, request.force))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {"scan_id": scan_id, "status": "started", "target_id": str(target.id)}


@router.get("/cache-status/{target_id}")
async def cache_status(target_id: str):
    """Whether a cached result already exists for this target — lets the UI offer
    'reuse last results' vs 'rescan' before spending time on a live scan."""
    try:
        target = await Target.get(PydanticObjectId(target_id))
    except Exception:
        target = None
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    info = await cache.has_cached(target.targetType.upper(), target.value)

    # Surface when the previous scan ran, if we have a log for it.
    last = await ScanLog.find(ScanLog.target_value == target.value).sort(-ScanLog.created_at).limit(1).to_list()
    info["last_scan_at"] = last[0].created_at.isoformat() if last else None
    info["last_findings"] = last[0].findings if last else None
    return info


@router.get("/progress/{scan_id}")
async def get_progress(scan_id: str):
    state = progress_store.get(scan_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return state


def _compute_metrics(raw: dict) -> dict:
    """Derive dashboard metrics (subdomains / endpoints / ports) from a stored
    pipeline result, regardless of which pipeline (URL / DNS / machine) produced it."""
    subdomains = 0
    endpoints = 0
    ports = 0

    if isinstance(raw, dict):
        # Sous-domaines (DNS pipeline — subfinder)
        sf = raw.get("subfinder_result", {})
        if isinstance(sf, dict):
            subdomains = len(sf.get("subfinder_subdomains", []) or [])

        # Endpoints actifs : hôtes live (httpx) + endpoints crawlés (katana)
        # + ressources brute-forcées (feroxbuster)
        hx = raw.get("httpx_result", [])
        if isinstance(hx, list):
            endpoints += len(hx)
        kat = raw.get("katana_result", {})
        if isinstance(kat, dict):
            endpoints += len(kat.get("katana_endpoints", []) or [])
        fx = raw.get("feroxbuster_result", {})
        if isinstance(fx, dict):
            endpoints += len(fx.get("feroxbuster_resources", []) or [])

        # Ports ouverts (machine pipeline — nmap)
        nm = raw.get("nmap_result", {})
        if isinstance(nm, dict):
            ports = len(nm.get("open_ports", []) or [])

    return {"subdomains": subdomains, "endpoints": endpoints, "ports": ports}


@router.get("/results/{target_id}")
async def get_results(target_id: str):
    results = await ScanResult.find(ScanResult.target_id == target_id).to_list()
    vulnerabilities = []
    metrics = {"subdomains": 0, "endpoints": 0, "ports": 0}
    for result in results:
        for vuln in result.vulnerabilities:
            vulnerabilities.append({
                "title": vuln.title,
                "description": vuln.description,
                "severity": vuln.severity,
                "tool": result.toolName,
            })
        m = _compute_metrics(result.rawJson)
        metrics["subdomains"] += m["subdomains"]
        metrics["endpoints"] += m["endpoints"]
        metrics["ports"] += m["ports"]

    metrics["findings"] = len(vulnerabilities)
    return {"vulnerabilities": vulnerabilities, "total": len(vulnerabilities), "metrics": metrics}


@router.get("/logs")
async def get_logs(limit: int = 100):
    """Return the history of searched sites, most recent first."""
    logs = await ScanLog.find_all().sort(-ScanLog.created_at).limit(limit).to_list()
    return {
        "logs": [
            {
                "id": str(log.id),
                "target_value": log.target_value,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "status": log.status,
                "subdomains": log.subdomains,
                "endpoints": log.endpoints,
                "ports": log.ports,
                "findings": log.findings,
                "duration_ms": log.duration_ms,
                "cached": log.cached,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "total": len(logs),
    }


def _build_report(target, scan_result) -> dict:
    """Assemble a detailed, human-readable report from a stored scan result."""
    raw = scan_result.rawJson if scan_result else {}
    metrics = _compute_metrics(raw)

    # Open ports (machine pipeline)
    nmap = raw.get("nmap_result", {}) if isinstance(raw, dict) else {}
    open_ports = [
        {
            "port": p.get("port"),
            "protocol": p.get("protocol"),
            "service": p.get("service"),
            "product": p.get("product"),
            "version": p.get("version"),
        }
        for p in (nmap.get("open_ports", []) or [])
    ]

    # Subdomains (DNS pipeline)
    subfinder = raw.get("subfinder_result", {}) if isinstance(raw, dict) else {}
    subdomains = subfinder.get("subfinder_subdomains", []) or []

    # Live HTTP endpoints (httpx)
    httpx_raw = raw.get("httpx_result", []) if isinstance(raw, dict) else []
    live_endpoints = []
    if isinstance(httpx_raw, list):
        for h in httpx_raw:
            if isinstance(h, dict):
                live_endpoints.append({
                    "url": h.get("url"),
                    "status_code": h.get("status_code"),
                    "title": h.get("title"),
                    "webserver": h.get("webserver"),
                    "tech": h.get("tech", []),
                })

    # Crawled endpoints (katana) + brute-forced resources (feroxbuster)
    katana = raw.get("katana_result", {}) if isinstance(raw, dict) else {}
    crawled = katana.get("katana_endpoints", []) or []
    ferox = raw.get("feroxbuster_result", {}) if isinstance(raw, dict) else {}
    resources = ferox.get("feroxbuster_resources", []) or []

    # Vulnerabilities grouped by severity
    vulns = []
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    if scan_result:
        for v in scan_result.vulnerabilities:
            sev = (v.severity or "info").lower()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            vulns.append({
                "title": v.title,
                "description": v.description,
                "severity": v.severity,
            })

    return {
        "report_type": "detailed_scan_report",
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "target": {
            "value": target.value,
            "type": target.targetType,
            "id": str(target.id),
        },
        "summary": {
            **metrics,
            "vulnerabilities": len(vulns),
            "severity_breakdown": severity_counts,
        },
        "open_ports": open_ports,
        "os_info": nmap.get("os_info", {}) if isinstance(nmap, dict) else {},
        "subdomains": subdomains,
        "live_endpoints": live_endpoints,
        "crawled_endpoints": crawled,
        "discovered_resources": resources,
        "vulnerabilities": vulns,
    }


@router.get("/report/{target_id}")
async def get_report(target_id: str):
    """Return a detailed downloadable report for the most recent scan of a target."""
    try:
        target = await Target.get(PydanticObjectId(target_id))
    except Exception:
        target = None
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    results = await ScanResult.find(ScanResult.target_id == target_id).sort(-ScanResult.created_at).to_list()
    scan_result = results[0] if results else None

    report = _build_report(target, scan_result)

    safe_name = target.value.replace("://", "_").replace("/", "_").replace(":", "_")
    headers = {
        "Content-Disposition": f'attachment; filename="report-{safe_name}.json"'
    }
    return JSONResponse(content=report, headers=headers)


@router.get("/report/{target_id}/pdf")
async def get_report_pdf(target_id: str):
    """Return the detailed report as a formatted PDF document."""
    try:
        target = await Target.get(PydanticObjectId(target_id))
    except Exception:
        target = None
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    results = await ScanResult.find(ScanResult.target_id == target_id).sort(-ScanResult.created_at).to_list()
    scan_result = results[0] if results else None

    report = _build_report(target, scan_result)

    from app.core.report_pdf import build_report_pdf
    pdf_bytes = build_report_pdf(report)

    safe_name = target.value.replace("://", "_").replace("/", "_").replace(":", "_")
    headers = {
        "Content-Disposition": f'attachment; filename="report-{safe_name}.pdf"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


async def check_tool_status(tool_name: str, version_arg: str = "--version") -> dict:
    """Check if a tool is available in PATH and runs correctly."""
    # httpx-toolkit is the Kali package name; on other platforms the tool is just "httpx"
    resolved_path = shutil.which(tool_name)
    if resolved_path is None and tool_name == "httpx-toolkit":
        resolved_path = shutil.which("httpx")
    if resolved_path is None:
        return {"status": "MISSING", "version": None, "error": "Not found in PATH"}

    try:
        process = await asyncio.create_subprocess_exec(
            resolved_path, version_arg,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=2.0)

        if process.returncode == 0:
            version_output = stdout.decode().strip().split("\n")[0] if stdout else "Available"
            return {"status": "OK", "version": version_output[:50], "error": None}
        else:
            error_msg = stderr.decode().strip() or stdout.decode().strip()
            return {"status": "ERROR", "version": None, "error": f"Exit code {process.returncode}: {error_msg[:100]}"}

    except asyncio.TimeoutError:
        return {"status": "TIMEOUT", "version": None, "error": "Tool took too long to respond"}
    except Exception as e:
        return {"status": "ERROR", "version": None, "error": str(e)}


@router.post("/health_check")
async def health_check(request: ScanRequest):
    tools_to_check = {
        "nmap":        "-V",
        "subfinder":   "--version",
        "httpx-toolkit": "--version",
        "katana":      "--version",
        "feroxbuster": "-V",
        "nuclei":      "--version",
    }

    tasks = {tool: check_tool_status(tool, arg) for tool, arg in tools_to_check.items()}
    tools_results = {}
    global_healthy = True

    for tool, task in tasks.items():
        result = await task
        tools_results[tool] = result
        if result["status"] != "OK":
            global_healthy = False

    return {
        "state": "healthy" if global_healthy else "degraded",
        "tools": tools_results,
    }


@router.post("/stop")
async def stop_scan():
    return {"message": "Scan stopped"}
