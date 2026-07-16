import os
import shutil
from pathlib import Path


def resolve_httpx() -> str | None:
    """Locate the ProjectDiscovery httpx binary.

    Kali packages it as ``httpx-toolkit``. When running inside a Python
    virtualenv, ``shutil.which("httpx")`` can instead resolve to the Python
    ``httpx[cli]`` shim (the HTTP client library), which is NOT the pentest
    tool and fails at runtime. So we check the Go install location explicitly
    before falling back to a bare PATH lookup.
    """
    candidates = [shutil.which("httpx-toolkit")]

    go_bin = Path.home() / "go" / "bin" / ("httpx.exe" if os.name == "nt" else "httpx")
    if go_bin.exists():
        candidates.append(str(go_bin))

    candidates.append(shutil.which("httpx"))

    for candidate in candidates:
        if candidate:
            return candidate
    return None
