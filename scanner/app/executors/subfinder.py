import asyncio
import json
import os
import shutil
from datetime import datetime
from app.Exception.tools_exception import ToolInternalError, ToolNotFoundError
from app.executors.base import Executor
from app.models.target import Target
from app.models.scan_result import ScanResult, Vulnerability

class SubfinderExecutor(Executor):

    def parse(self, stdout: bytes) -> list:
        subdomains = []
        raw_lines = stdout.decode().strip().split("\n")
        raw_json_list = []

        for line in raw_lines:
            if not line.strip():
                continue
            try:
                parsed_json = json.loads(line.strip())
                raw_json_list.append(parsed_json)
                # subfinder -json renvoie {"host": "...", "input": "...", "source": "..."}
                host = parsed_json.get("host", "")
                if host:
                    subdomains.append(host)
            except Exception:
                # Certaines versions/sources renvoient une ligne brute (juste le sous-domaine)
                # plutot que du JSON, on la recupere quand meme
                stripped = line.strip()
                if stripped:
                    subdomains.append(stripped)

        # Deduplicate
        subdomains = list(set(subdomains))
        return subdomains

    async def excutor(self, data: dict) -> dict:
        domain = data.get("domain", data.get("url", "unknown"))

        # Check if we should use mock or real execution
        subfinder_path = shutil.which("subfinder")
        if subfinder_path is None:
            raise ToolNotFoundError("subfinder", "subfinder tool not found")

        # Command: subfinder -d <domain> -silent -json
        proc = await asyncio.create_subprocess_exec(
            subfinder_path, "-d", domain, "-silent", "-json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        print("subfinder", stdout, stderr)

        #! Comme pour httpx : une enumeration vide n'est pas forcement une erreur,
        #! mais un returncode != 0 signale un vrai probleme (domaine invalide, source down, etc.)
        if proc.returncode != 0:
            raise ToolInternalError(stderr.decode(), tool_name="subfinder", message="Tool returned non-zero exit status.")

        subdomains = self.parse(stdout)

        data["subfinder_result"] = {
            "subfinder_status": "completed",
            "subfinder_subdomains": subdomains,
        }
        return data