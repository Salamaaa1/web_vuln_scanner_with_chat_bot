import asyncio
import json
import os
import shutil
from datetime import datetime, timezone
from app.Exception.tools_exception import ToolInternalError, ToolNotFoundError
from app.executors.base import Executor
from app.models.scan_result import ScanResult

class KatanaExecutor(Executor):

    def parse(self, stdout: bytes) -> list:
        endpoints = []
        raw_lines = stdout.decode().strip().split("\n")
        
        seen_keys = set() # Pour éviter les doublons stricts (URL + Méthode)

        for line in raw_lines:
            if not line.strip():
                continue
            try:
                parsed_json = json.loads(line.strip())
                
                # Extraction intelligente de l'URL. Katana v1 writes it as
                # request.endpoint; older versions used request.url / url.
                req = parsed_json.get("request", {}) or {}
                discovered_url = (req.get("endpoint") or req.get("url")
                                  or parsed_json.get("endpoint") or parsed_json.get("url") or "")
                method = req.get("method", "GET")
                
                if discovered_url:
                    # Clé d'unicité basée sur l'URL et la méthode de requête
                    uniq_key = f"{method}:{discovered_url}"
                    if uniq_key not in seen_keys:
                        seen_keys.add(uniq_key)
                        
                        endpoints.append({
                            "url": discovered_url,
                            "method": method,
                            "source": parsed_json.get("source", "crawler"),
                            "has_form": "form" in parsed_json or bool(parsed_json.get("form"))
                        })
            except Exception:
                pass
        
        return endpoints

    async def excutor(self, data: dict) -> dict:
        url = data.get("url", data.get("domain", "unknown"))
        
        result = {}
        katana_path = shutil.which("katana")
        if katana_path is None:
            raise ToolNotFoundError("katana", "katana tool not found")
        
        # Exécution de la commande
        proc = await asyncio.create_subprocess_exec(
            katana_path, "-u", url,
            "-js-crawl", "-automatic-form-fill", "-form-extraction", "-known-files", "all",
            "-jsonl", "-silent",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise ToolInternalError(stderr.decode(), tool_name="katana", message="Tool returned non-zero exit status.")
        
        endpoints = self.parse(stdout)
        
        # ! Vérification si aucune connexion ou aucun endpoint trouvé
        if not endpoints:
            result["katana_status"] = "failed_or_empty"
            result["katana_endpoints"] = []
            data["katana_result"]  = result
            return data 
            
        result["katana_status"] = "completed"
        result["katana_endpoints"] = endpoints

        data["katana_result"]  = result 
        return data