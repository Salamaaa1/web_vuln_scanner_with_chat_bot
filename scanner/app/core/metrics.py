"""Dashboard counters (subdomains / endpoints / ports) derived from pipeline results.

Shared by the final results endpoint and the live progress updates, so the
numbers shown during a scan and after it are computed the same way.
"""


def compute_metrics(raw: dict) -> dict:
    """Derive dashboard metrics from a (possibly partial) pipeline result,
    regardless of which pipeline (URL / DNS / machine) produced it."""
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
