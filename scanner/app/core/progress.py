"""In-process progress tracking for running scans.

A scan runs as a background asyncio task inside the uvicorn worker; the frontend
polls GET /scans/progress/{scan_id} to stream step-by-step updates to the live
console. State is kept in a module-level dict — reliable for a single worker
process (the default deployment). For a multi-worker deployment, back this with
Redis pub/sub instead.
"""
import datetime
from typing import Optional

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
    }


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
