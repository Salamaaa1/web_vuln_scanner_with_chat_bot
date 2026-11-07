import asyncio
import json
import os
import shutil
import signal
import tempfile
from urllib.parse import parse_qsl, urlsplit
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

        seen = set()
        for line in raw_lines:
            if not line.strip():
                continue
            try:
                val = json.loads(line.strip())
                if not isinstance(val, dict):
                    continue
                # Same template on the same URL = same finding (e.g. found by
                # both the standard and the DAST pass).
                key = (val.get("template-id"), val.get("matched-at") or val.get("host"))
                if key in seen:
                    continue
                seen.add(key)
                # Raw HTTP request/response can be huge; keep a readable excerpt
                # so stored results stay small (MongoDB 16 MB document limit).
                for field in ("request", "response"):
                    if isinstance(val.get(field), str) and len(val[field]) > 2000:
                        val[field] = val[field][:2000] + "\n...[truncated]"
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




    # ------------------------------------------------------------------
    # Targets
    # ------------------------------------------------------------------
    @staticmethod
    def _origin(url: str):
        """scheme://host[:port] of a URL, or None."""
        try:
            p = urlsplit(url)
        except Exception:
            return None
        if p.scheme in ("http", "https") and p.netloc:
            return f"{p.scheme}://{p.netloc}"
        return None

    def extract_urls(self, data: dict) -> list:
        """Targets for the standard templates: the scanned URL plus every live
        host. Nuclei's standard templates probe their own paths (/.git/config,
        /admin, known CVE paths...) from the base URL, so running them against
        every crawled page only multiplies requests without finding more."""
        targets = []

        def add(u):
            if u and u not in targets:
                targets.append(u)

        if data.get("url"):
            add(data["url"])
            add(self._origin(data["url"]))
        for res in data.get("httpx_result", []) if isinstance(data.get("httpx_result"), list) else []:
            if isinstance(res, dict) and res.get("url"):
                add(res["url"])
        if not targets and data.get("ip"):
            add(data["ip"])
        return targets

    def extract_dast_urls(self, data: dict) -> list:
        """Pages with query parameters, for DAST fuzzing (XSS, SQLi, LFI,
        open redirect...). One URL per (path + parameter names), capped."""
        max_urls = int(os.getenv("NUCLEI_DAST_MAX_URLS", "150"))
        urls, seen = [], set()

        candidates = []
        kat = data.get("katana_result", {})
        if isinstance(kat, dict):
            candidates += [e.get("url") for e in kat.get("katana_endpoints", []) or [] if isinstance(e, dict)]
        fx = data.get("feroxbuster_result", {})
        if isinstance(fx, dict):
            candidates += [r.get("url") for r in fx.get("feroxbuster_resources", []) or [] if isinstance(r, dict)]
        if data.get("url"):
            candidates.append(data["url"])

        for u in candidates:
            if not u or "?" not in u:
                continue
            p = urlsplit(u)
            params = tuple(sorted(k for k, _ in parse_qsl(p.query, keep_blank_values=True)))
            if not params:
                continue
            key = (p.netloc.lower(), p.path, params)
            if key in seen:
                continue
            seen.add(key)
            urls.append(u)
            if len(urls) >= max_urls:
                break
        return urls

    # ------------------------------------------------------------------
    # Running nuclei
    # ------------------------------------------------------------------
    async def _run(self, cmd: list, timeout: float):
        """Run one nuclei command, reporting each finding live as it is
        printed. Stops nuclei after `timeout` seconds and keeps what it found.
        Returns (stdout_bytes, stderr_text, returncode, timed_out)."""
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
        stderr_text = stderr.decode(errors="replace")
        print("nuclei rc", proc.returncode, "timed_out", timed_out, "stderr:", stderr_text[:300])
        return b"".join(out_lines), stderr_text, proc.returncode, timed_out

    @staticmethod
    def _base_cmd(nuclei_path: str, list_file: str) -> list:
        # -duc: no update check at scan time (templates are installed in the
        # image at build time; checking/updating mid-scan only slows it down).
        cmd = [nuclei_path, "-l", list_file, "-jsonl", "-silent", "-duc",
               "-timeout", "10", "-retries", "1", "-no-color"]
        severity = os.getenv("NUCLEI_SEVERITY", "").strip()
        if severity:
            cmd += ["-severity", severity]
        # Extra flags, e.g. "-c 5 -bs 5 -rl 50" to keep memory/CPU low on small servers.
        cmd += os.getenv("NUCLEI_EXTRA_ARGS", "").split()
        return cmd

    @staticmethod
    def _write_list(urls: list) -> str:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            for u in urls:
                f.write(f"{u}\n")
            return f.name

    async def excutor(self, data: dict) -> dict:
        nuclei_path = shutil.which("nuclei")
        if nuclei_path is None:
            raise ToolNotFoundError("nuclei", "nuclei tool not found")

        url_list = self.extract_urls(data)
        if not url_list:
            raise NoDataFoundError(tool_name="nuclei")
        dast_urls = self.extract_dast_urls(data) if os.getenv("NUCLEI_DAST", "1") != "0" else []

        temp_files = []
        try:
            # 1. Standard templates (CVEs, misconfigurations, exposures...) on
            #    the target and its live hosts.
            base_file = self._write_list(url_list)
            temp_files.append(base_file)
            cmd = self._base_cmd(nuclei_path, base_file)
            tags = os.getenv("NUCLEI_TAGS", "").strip()
            if tags:
                cmd += ["-tags", tags]
            out, err, rc, timed_out = await self._run(cmd, float(os.getenv("NUCLEI_TIMEOUT", "600")))

            # Nuclei can exit non-zero for benign reasons (e.g. a target went
            # unresponsive) while still producing findings. Only a run that
            # failed outright with nothing to fuzz afterwards is an error.
            if rc != 0 and not out.strip() and not timed_out and not dast_urls:
                raise ToolInternalError(err, tool_name="nuclei", message="Tool returned non-zero exit status.")

            # 2. DAST fuzzing of pages with parameters (XSS, SQLi, LFI, SSRF,
            #    open redirect...). A failure here never cancels step 1.
            dast_out, dast_timed_out, dast_error = b"", False, None
            if dast_urls:
                dast_file = self._write_list(dast_urls)
                temp_files.append(dast_file)
                dcmd = self._base_cmd(nuclei_path, dast_file) + ["-dast"]
                dast_out, derr, drc, dast_timed_out = await self._run(
                    dcmd, float(os.getenv("NUCLEI_DAST_TIMEOUT", "300")))
                if drc != 0 and not dast_out.strip() and not dast_timed_out:
                    dast_error = derr.strip()[:300] or f"exit code {drc}"
        finally:
            for f in temp_files:
                try:
                    os.remove(f)
                except OSError:
                    pass

        result = self.parse(out + b"\n" + dast_out, url_list)
        result["timed_out"] = timed_out or dast_timed_out
        result["scanned_targets"] = len(url_list)
        result["dast_targets"] = len(dast_urls)
        if dast_error:
            result["dast_error"] = dast_error
        result["nuclei_status"] = "completed"
        data["nuclei_result"] = result
        return data
