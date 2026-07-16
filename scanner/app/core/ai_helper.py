"""LLM-backed remediation advisor.

Given a vulnerability (title / description / severity), asks an OpenAI-compatible
LLM (NVIDIA NIM by default) for a concise "bilan": what the issue is, its impact,
and concrete steps to fix it. Results are cached in Redis by vulnerability title
so the same finding is never re-billed to the model twice.
"""
import asyncio
import hashlib
import json
import os
from typing import Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

from app.core import cache as cache_module

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v4-flash")

_client = None


def is_configured() -> bool:
    return bool(NVIDIA_API_KEY) and OpenAI is not None


def _get_client():
    global _client
    if not is_configured():
        return None
    if _client is None:
        _client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)
    return _client


SYSTEM_PROMPT = (
    "You are a senior application-security engineer helping a pentester. "
    "For the given vulnerability finding, produce a short, practical assessment. "
    "Respond ONLY with a valid JSON object with exactly these keys:\n"
    '  "analysis"   - 2-3 sentences: what the vulnerability is and its concrete impact/risk.\n'
    '  "remediation"- 3-6 short, actionable steps to fix it (as a single string, use "- " bullets and newlines).\n'
    '  "severity"   - one of: critical, high, medium, low, info (your judgment).\n'
    "Be specific and technical. No preamble, no markdown fences, JSON only."
)


def _cache_key(title: str) -> str:
    h = hashlib.sha1(title.strip().lower().encode()).hexdigest()[:16]
    return f"ai:bilan:{h}"


def _parse_json(text: str) -> Optional[dict]:
    text = (text or "").strip()
    # strip ```json ... ``` fences if present
    if text.startswith("```"):
        text = text.split("```", 2)[1] if "```" in text[3:] else text
        text = text.lstrip("json").strip("`").strip()
    # find the outermost JSON object
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    try:
        return json.loads(text)
    except Exception:
        return None


async def explain_vulnerability(title: str, description: str = "", severity: str = "",
                                use_cache: bool = True) -> dict:
    """Return {analysis, remediation, severity} for one vulnerability.

    Raises RuntimeError if the LLM isn't configured. Cheap failures (bad JSON,
    network) are wrapped in a structured 'error' bilan instead of raising.
    """
    if not is_configured():
        raise RuntimeError("AI helper not configured (missing NVIDIA_API_KEY).")

    key = _cache_key(title)

    if use_cache:
        client = await cache_module.get_client()
        if client is not None:
            try:
                raw = await client.get(key)
                if raw:
                    return json.loads(raw)
            except Exception:
                pass

    user_prompt = (
        f"Vulnerability title: {title}\n"
        f"Reported severity: {severity or 'unknown'}\n"
        f"Description: {description or '(none provided)'}\n"
    )

    llm = _get_client()

    def _call():
        completion = llm.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            top_p=0.95,
            max_tokens=1200,
            stream=False,
        )
        return completion.choices[0].message.content or ""

    try:
        # The OpenAI SDK call is blocking — run it off the event loop.
        # The NIM endpoint returns transient 503 "ResourceExhausted" under load,
        # so retry a couple of times with backoff before giving up.
        last_err = None
        content = None
        for attempt in range(3):
            try:
                content = await asyncio.wait_for(asyncio.to_thread(_call), timeout=60)
                break
            except Exception as err:
                last_err = err
                if attempt < 2:
                    await asyncio.sleep(2 * (attempt + 1))
        if content is None:
            raise last_err
    except Exception as e:
        return {
            "analysis": f"AI request failed: {e}",
            "remediation": "Retry later, or consult the vulnerability reference manually.",
            "severity": severity or "info",
            "error": True,
        }

    parsed = _parse_json(content)
    if not parsed:
        # Model returned prose instead of JSON — surface it as the analysis.
        parsed = {
            "analysis": content.strip()[:1500] or "No response.",
            "remediation": "See analysis above.",
            "severity": severity or "info",
        }

    result = {
        "analysis": str(parsed.get("analysis", "")).strip(),
        "remediation": str(parsed.get("remediation", "")).strip(),
        "severity": str(parsed.get("severity", severity or "info")).strip().lower(),
    }

    # cache it
    if use_cache:
        client = await cache_module.get_client()
        if client is not None:
            try:
                await client.set(key, json.dumps(result), ex=7 * 24 * 3600)
            except Exception:
                pass

    return result


FOLLOWUP_SYSTEM = (
    "You are a senior application-security engineer. The user is asking a follow-up "
    "question about a specific vulnerability found in their pentest scan. "
    "Answer concisely and technically in plain text (no JSON, no markdown fences). "
    "Stay focused on this vulnerability and its remediation."
)


async def ask_followup(title: str, severity: str, bilan: dict,
                       history: list, question: str) -> str:
    """Answer a follow-up question about one vulnerability, given its bilan and
    prior Q&A history. Returns plain text."""
    if not is_configured():
        raise RuntimeError("AI helper not configured (missing NVIDIA_API_KEY).")

    context = (
        f"Vulnerability: {title}\n"
        f"Severity: {severity or 'unknown'}\n"
        f"Prior analysis: {bilan.get('analysis', '')}\n"
        f"Prior remediation: {bilan.get('remediation', '')}\n"
    )

    messages = [
        {"role": "system", "content": FOLLOWUP_SYSTEM},
        {"role": "user", "content": context},
    ]
    # Replay stored history so the model keeps context across questions.
    for m in history[-10:]:
        role = m.get("role") if isinstance(m, dict) else getattr(m, "role", None)
        content = m.get("content") if isinstance(m, dict) else getattr(m, "content", None)
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})

    llm = _get_client()

    def _call():
        completion = llm.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=messages,
            temperature=0.4,
            top_p=0.95,
            max_tokens=1200,
            stream=False,
        )
        return completion.choices[0].message.content or ""

    try:
        return (await asyncio.wait_for(asyncio.to_thread(_call), timeout=60)).strip()
    except Exception as e:
        return f"La requête IA a échoué : {e}"
