"""Redis-backed cache for scan results.

Caching lets a repeated search for the same target return instantly instead of
re-running the whole tool pipeline. The cache degrades gracefully: if Redis is
unreachable, every operation becomes a no-op and scans simply run live.
"""
import json
import os
from typing import Optional

try:
    from redis import asyncio as aioredis
except Exception:  # redis not installed
    aioredis = None

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
# Time-to-live for a cached scan result, in seconds (default 1h).
CACHE_TTL = int(os.getenv("SCAN_CACHE_TTL", "3600"))

_client = None


async def get_client():
    """Return a shared async Redis client, or None if Redis is unavailable."""
    global _client
    if aioredis is None:
        return None
    if _client is None:
        try:
            _client = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
            await _client.ping()
        except Exception:
            _client = None
    return _client


def scan_key(target_type: str, value: str) -> str:
    return f"scan:{target_type.upper()}:{value.strip().lower()}"


async def get_cached(target_type: str, value: str) -> Optional[dict]:
    client = await get_client()
    if client is None:
        return None
    try:
        raw = await client.get(scan_key(target_type, value))
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def has_cached(target_type: str, value: str) -> dict:
    """Cheap existence check (no payload fetch). Returns {cached, ttl}."""
    client = await get_client()
    if client is None:
        return {"cached": False, "ttl": 0}
    try:
        key = scan_key(target_type, value)
        exists = await client.exists(key)
        ttl = await client.ttl(key) if exists else 0
        return {"cached": bool(exists), "ttl": int(ttl or 0)}
    except Exception:
        return {"cached": False, "ttl": 0}


async def set_cached(target_type: str, value: str, data: dict) -> None:
    client = await get_client()
    if client is None:
        return
    try:
        await client.set(scan_key(target_type, value), json.dumps(data, default=str), ex=CACHE_TTL)
    except Exception:
        pass


async def clear_cached(target_type: str, value: str) -> None:
    client = await get_client()
    if client is None:
        return
    try:
        await client.delete(scan_key(target_type, value))
    except Exception:
        pass
