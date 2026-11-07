"""In-process progress tracking for running scans.

A scan runs as a background asyncio task inside the uvicorn worker; the frontend
polls GET /scans/progress/{scan_id} to stream step-by-step updates to the live
console. State is kept in a module-level dict — reliable for a single worker
process (the default deployment). For a multi-worker deployment, back this with
Redis pub/sub instead.
"""
import contextvars
import datetime
from typing import Optional

# Which scan the current asyncio task belongs to. Set once per scan job with
# bind(); every task the pipeline starts inherits it, so executors can report
# live results with report_finding()/report_partial() without extra arguments.
_current_scan: contextvars.ContextVar = contextvars.ContextVar("current_scan_id", default=None)

# scan_id -> {status, events: [...], results_count, target_id, cached}
_STORE: dict = {}
# Keep the store from growing unbounded across a long-lived process.
_MAX_SCANS = 200


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def create(scan_id: str, target_id: Optional[str] = None) -> None:
    if len(_STORE) >= _MAX_SCANS:
        # Drop the oldest entries.
        for key in list(_STORE.keys())[: len(_STORE) - _MAX_SCANS + 1]:
            _STORE.pop(key, None)
    _STORE[scan_id] = {
        "status": "running",
        "events": [],
        "results_count": 0,
        "target_id": target_id,
        "cached": False,
        "created_at": _now(),
        # Live results, filled while the scan runs (shown by the dashboard).
        "findings": [],
        "metrics": {"subdomains": 0, "endpoints": 0, "ports": 0, "findings": 0},
        # Live lists (hosts, endpoints, resources, ports, subdomains).
        "inventory": None,
    }


def bind(scan_id: str) -> None:
    """Attach the current asyncio task (and the tasks it starts) to a scan."""
    _current_scan.set(scan_id)


def _current_entry() -> Optional[dict]:
    scan_id = _current_scan.get()
    return _STORE.get(scan_id) if scan_id else None


def report_finding(finding: dict) -> None:
    """Called by an executor as soon as it finds a vulnerability."""
    entry = _current_entry()
    if entry is None:
        return
    entry["findings"].append(finding)
    entry["metrics"]["findings"] = len(entry["findings"])


def report_partial(results: dict) -> None:
    """Called when a tool finishes, with the pipeline results so far."""
    entry = _current_entry()
    if entry is None:
        return
    from app.core.metrics import build_inventory, limit_inventory
    inv = build_inventory(results)
    counts = {"subdomains": len(inv["subdomains"]), "endpoints": inv["unique_urls"], "ports": len(inv["ports"])}
    for key, value in counts.items():
        # Counters only ever go up while a scan runs.
        entry["metrics"][key] = max(entry["metrics"].get(key, 0), value)
    entry["inventory"] = limit_inventory(inv)


def push(scan_id: str, message: str, level: str = "info") -> None:
    entry = _STORE.get(scan_id)
    if entry is None:
        return
    entry["events"].append({"ts": _now(), "message": message, "level": level})


def finish(scan_id: str, status: str = "completed", results_count: int = 0,
           cached: bool = False) -> None:
    entry = _STORE.get(scan_id)
    if entry is None:
        return
    entry["status"] = status
    entry["results_count"] = results_count
    entry["cached"] = cached


def get(scan_id: str) -> Optional[dict]:
    return _STORE.get(scan_id)
