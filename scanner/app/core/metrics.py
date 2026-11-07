"""What a scan found, in one consistent shape.

`build_inventory()` turns the raw tool results into de-duplicated lists
(hosts, endpoints, resources, ports, subdomains). The dashboard counters, the
live progress view and the PDF/JSON report all use it, so the numbers shown
during a scan, after it, and in the report always agree.
"""
from urllib.parse import urlsplit, urlunsplit


def _norm_url(url: str) -> str:
    """Key used to de-duplicate URLs: lower-case scheme/host, no trailing '/'
    on the path, no fragment. Query strings are kept (they are different pages)."""
    try:
        p = urlsplit(str(url).strip())
    except Exception:
        return str(url).strip()
    if not p.scheme or not p.netloc:
        return str(url).strip().rstrip("/")
    path = p.path.rstrip("/")
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, p.query, ""))


def build_inventory(raw: dict) -> dict:
    """De-duplicated hosts / endpoints / resources / ports / subdomains."""
    raw = raw if isinstance(raw, dict) else {}

    # Live hosts (httpx). httpx can report the same URL twice (e.g. with
    # -tls-probe), so keep the first entry per URL.
    hosts, seen = [], set()
    hx = raw.get("httpx_result", [])
    for h in hx if isinstance(hx, list) else []:
        if not isinstance(h, dict) or not h.get("url"):
            continue
        key = _norm_url(h["url"])
        if key in seen:
            continue
        seen.add(key)
        hosts.append({
            "url": h.get("url"),
            "status_code": h.get("status_code"),
            "title": h.get("title") or "",
            "webserver": h.get("webserver") or "",
            "tech": h.get("tech") or [],
        })

    # Crawled endpoints (katana)
    endpoints, seen = [], set()
    kat = raw.get("katana_result", {})
    for e in (kat.get("katana_endpoints", []) or []) if isinstance(kat, dict) else []:
        if not isinstance(e, dict) or not e.get("url"):
            continue
        method = (e.get("method") or "GET").upper()
        key = (method, _norm_url(e["url"]))
        if key in seen:
            continue
        seen.add(key)
        endpoints.append({"url": e["url"], "method": method, "has_params": "?" in e["url"]})

    # Brute-forced resources (feroxbuster)
    resources, seen = [], set()
    fx = raw.get("feroxbuster_result", {})
    for r in (fx.get("feroxbuster_resources", []) or []) if isinstance(fx, dict) else []:
        if not isinstance(r, dict) or not r.get("url"):
            continue
        key = _norm_url(r["url"])
        if key in seen:
            continue
        seen.add(key)
        resources.append({"url": r["url"], "status_code": r.get("status_code")})

    # Open ports (nmap)
    nm = raw.get("nmap_result", {})
    nm = nm if isinstance(nm, dict) else {}
    ports = [
        {
            "port": p.get("port"),
            "protocol": p.get("protocol") or "tcp",
            "service": p.get("service") or "",
            "product": p.get("product") or "",
            "version": p.get("version") or "",
        }
        for p in (nm.get("open_ports", []) or []) if isinstance(p, dict)
    ]

    # Subdomains (subfinder)
    sf = raw.get("subfinder_result", {})
    subdomains = sorted(set(sf.get("subfinder_subdomains", []) or [])) if isinstance(sf, dict) else []

    # One URL found by several tools counts once.
    unique_urls = {_norm_url(x["url"]) for x in hosts + endpoints + resources}

    return {
        "hosts": hosts,
        "endpoints": endpoints,
        "resources": resources,
        "ports": ports,
        "subdomains": subdomains,
        "os_info": nm.get("os_info", {}) or {},
        "port_scan_done": nm.get("status") == "completed",
        "unique_urls": len(unique_urls),
    }


def compute_metrics(raw: dict) -> dict:
    """Dashboard counters, derived from the same inventory as the report."""
    inv = build_inventory(raw)
    return {
        "subdomains": len(inv["subdomains"]),
        "endpoints": inv["unique_urls"],
        "ports": len(inv["ports"]),
    }


def limit_inventory(inv: dict, max_items: int = 500) -> dict:
    """Same inventory with long lists capped (for frequent live updates)."""
    out = dict(inv)
    for key in ("hosts", "endpoints", "resources", "ports", "subdomains"):
        out[key] = inv.get(key, [])[:max_items]
    return out
