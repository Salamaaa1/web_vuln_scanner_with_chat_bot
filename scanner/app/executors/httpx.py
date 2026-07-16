import asyncio
import json
import os
import shutil
from datetime import datetime, timezone
from app.Exception.tools_exception import ToolInternalError  , ToolNotFoundError
from app.executors.base import Executor
from app.executors.tool_utils import resolve_httpx
from app.models.scan_result import ScanResult
import tempfile





class HttpxExecutor(Executor):
    async def excutor(self, data: dict) -> dict:
        httpx_path = resolve_httpx()
        if httpx_path is None:
            raise ToolNotFoundError("httpx-toolkit", "httpx tool not found")

        # Flags communs pour tous les modes
        common_flags = [
            "-status-code", "-tech-detect", "-title", "-server", 
            "-favicon", "-cname", "-cdn", "-tls-probe", 
            "-content-length", "-location", "-json", "-silent"
        ]

        temp_file_path = None
        cmd_args = [httpx_path] + common_flags

        # 1. Logique de sélection : Nmap (liste) vs URL unique
        nmap_result = data.get("nmap_result", {})
        if nmap_result and nmap_result.get("open_ports"):
            ip = data.get("ip")
            urls = [f"http://{ip}:{p['port']}" for p in nmap_result.get("open_ports", []) if p['port'] in [80, 443, 8080, 8443]]
            
            if urls:
                # Création du fichier temporaire pour le mode liste
                with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as temp_file:
                    for u in urls:
                        temp_file.write(f"{u}\n")
                    temp_file_path = temp_file.name
                cmd_args.extend(["-l", temp_file_path])
            else:
                return data # Rien à scanner
        else:
            # Mode URL unique
            url = data.get("url", data.get("domain", "unknown"))
            if url == "unknown":
                return data
            cmd_args.extend(["-u", url])

        # 2. Exécution commune
        proc = await asyncio.create_subprocess_exec(
            *cmd_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        # 3. Nettoyage du fichier temp si utilisé
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        if proc.returncode != 0:
            raise ToolInternalError(stderr.decode(), tool_name="httpx", message="Tool returned non-zero exit status.")

        # 4. Parsing (Gestion du multi-lignes pour le mode liste)
        results = []
        for line in stdout.decode().splitlines():
            if line.strip():
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        data["httpx_result"] = results
        return data