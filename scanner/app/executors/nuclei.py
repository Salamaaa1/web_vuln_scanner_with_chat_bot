import asyncio
import json
import os
import shutil
import signal
import tempfile
from datetime import datetime, timezone
from app.Exception.tools_exception import NoDataFoundError, ToolInternalError, ToolNotFoundError
from app.executors.base import Executor
from app.models.scan_result import ScanResult, Vulnerability
from app.core import progress as progress_store

# Severity mapping — Nuclei → standard labels
SEVERITY_MAP = {
    "critical": "critical",
    "high":     "high",
    "medium":   "medium",
    "low":      "low",
    "info":     "info",
    "unknown":  "info",
}

class NucleiExecutor(Executor):

    @staticmethod
    def _live_finding(line: bytes):
        """Turn one nuclei JSONL line into the small dict the dashboard shows
        live (same fields as GET /scans/results). None if it isn't a finding."""
        try:
            val = json.loads(line.decode(errors="replace").strip())
        except Exception:
            return None
        if not isinstance(val, dict):
            return None
        info = val.get("info", {}) or {}
        return {
            "title": info.get("name", val.get("template-id", "Unknown")),
            "description": info.get("description", ""),
            "severity": SEVERITY_MAP.get(str(info.get("severity", "info")).lower(), "info"),
            "tool": "nuclei",
            "target": val.get("matched-at") or val.get("host"),
        }

   
    def parse(self , stdout: bytes, url_list: list) -> dict:
        if url_list is None:
            url_list = []
    
        vulnerabilities = []
        raw_results = []
        raw_lines = stdout.decode().strip().split("\n")

        for line in raw_lines:
            if not line.strip():
                continue
            try:
                val = json.loads(line.strip())
                raw_results.append(val)

                info = val.get("info", {})
                severity_raw = info.get("severity", "info").lower()
                severity = SEVERITY_MAP.get(severity_raw, "info") # Assure-toi que SEVERITY_MAP est accessible

                # 1. On remplace l'objet Vulnerability par un dictionnaire standard
                vuln = {
                    "title": info.get("name", val.get("template-id", "Unknown")),
                    "description": info.get("description", ""),
                    "severity": severity,
                    "raw_data": val
                }
                vulnerabilities.append(vuln)
            except Exception:
                pass
             
        # 2. On remplace l'objet ScanResult par un dictionnaire global
        result = {
            "toolName": "nuclei",
            "status": "completed",
            "rawJson": {
                "results": raw_results, 
                "scanned_urls": url_list
            },
            "vulnerabilities": vulnerabilities  # Contient la liste de tes dictionnaires 'vuln'
        }

        return result




    def extract_urls(self, data: dict) -> list:
        urls_to_scan = set()
        
        # 1. Ajouter l'URL principale
        if data.get("url"):
            urls_to_scan.add(data["url"])
            
        # 2. Extraire les URLs trouvées par Katana
        
        katana_result = data.get("katana_result", {})
        katana_endpoints = katana_result.get("katana_endpoints", [])

       
          
        if isinstance(katana_endpoints, list):
            for endpoint in katana_endpoints:
                # endpoint est un dict (ex: {"url": "...", "method": "..."})
                u = endpoint.get("url")
                if u:
                    urls_to_scan.add(u)
                    
        httpx_res = data.get("httpx_result", [])
        if isinstance(httpx_res, list):
            for res in httpx_res:
                u = res.get("url")
                if u:
                    urls_to_scan.add(u)
        
                    
        # 3. Extraire les URLs trouvées par Feroxbuster
        feroxbuster_result = data.get("feroxbuster_result", {})
        feroxbuster_resources = feroxbuster_result.get("feroxbuster_resources", [])
        
        if isinstance(feroxbuster_resources, list):
            for resource in feroxbuster_resources:
                # resource est un dict (ex: {"url": "...", "status_code": 200})
                u = resource.get("url")
                if u:
                    urls_to_scan.add(u)
                    
        return list(urls_to_scan)
    

    async def excutor(self, data: dict) -> dict:

      
        # Check if we should use mock or real execution
        nuclei_path = shutil.which("nuclei")


        if nuclei_path is None:
            raise ToolNotFoundError("nuclei", "nuclei tool not found")


        # Consolidate URLs
        url_list = self.extract_urls(data)
        # Real Execution
        if not url_list:
            # Nothing to scan
            raise NoDataFoundError(tool_name="nuclei")

        temp_url_file = None

        
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as temp_file:
            for u in url_list:
                temp_file.write(f"{u}\n")
            temp_url_file = temp_file.name

        # Build the nuclei command.
        # By default we run the FULL default template set — that is what real
        # vulnerability detection needs. The previous narrow "-tags
        # cves,dast,misconfiguration" filter missed almost everything.
        # Both the tag filter and the severity filter are overridable via env
        # vars so an operator can trade coverage for speed.
        cmd = [nuclei_path, "-l", temp_url_file, "-jsonl", "-silent",
               "-timeout", "10", "-retries", "1", "-no-color"]

        tags = os.getenv("NUCLEI_TAGS", "").strip()
        if tags:
            cmd += ["-tags", tags]

        severity = os.getenv("NUCLEI_SEVERITY", "").strip()
        if severity:
            cmd += ["-severity", severity]

        # Extra flags, e.g. "-c 5 -bs 5 -rl 50" to keep memory/CPU low on small
        # servers.
        cmd += os.getenv("NUCLEI_EXTRA_ARGS", "").split()

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # JSONL lines include the raw HTTP request/response and can be
            # much larger than asyncio's 64 KiB default line limit.
            limit=32 * 1024 * 1024,
            # Own process group, so a timeout can stop nuclei and anything it spawned.
            start_new_session=(os.name != "nt"),
        )

        # Read findings as they are printed, under a hard time limit
        # (NUCLEI_TIMEOUT seconds, default 600). If the limit is hit, nuclei is
        # stopped and the findings collected so far are kept, so a slow target
        # or a small server never leaves the scan hanging forever.
        timeout = float(os.getenv("NUCLEI_TIMEOUT", "600"))
        out_lines = []

        async def _collect_stdout():
            async for line in proc.stdout:
                out_lines.append(line)
                live = self._live_finding(line)
                if live:
                    progress_store.report_finding(live)

        stderr_task = asyncio.create_task(proc.stderr.read())
        timed_out = False
        try:
            await asyncio.wait_for(_collect_stdout(), timeout=timeout)
            await proc.wait()
        except asyncio.TimeoutError:
            timed_out = True
            try:
                if os.name != "nt":
                    os.killpg(proc.pid, signal.SIGKILL)
                else:
                    proc.kill()
            except ProcessLookupError:
                pass
            await proc.wait()
        try:
            stderr = await asyncio.wait_for(stderr_task, timeout=5)
        except asyncio.TimeoutError:
            stderr_task.cancel()
            stderr = b""
        stdout = b"".join(out_lines)

        print("nuclei rc", proc.returncode, "timed_out", timed_out, "stderr:", stderr.decode(errors="replace")[:300])

        # Nuclei can exit non-zero for benign reasons (e.g. a target went
        # unresponsive) while still producing valid findings on stdout. Only
        # treat it as a hard failure if it produced no output at all.
        if proc.returncode != 0 and not stdout.strip() and not timed_out:
            raise ToolInternalError(stderr.decode(errors="replace"), tool_name="nuclei", message="Tool returned non-zero exit status.")

        result  =  self.parse(stdout , url_list)
        result["timed_out"] = timed_out

        result["nuclei_status"] = "completed"
        data["nuclei_result"] = result

        if temp_url_file and os.path.exists(temp_url_file):
            try:
                os.remove(temp_url_file)
            except Exception:
                pass
        return data

        
            
            
        
