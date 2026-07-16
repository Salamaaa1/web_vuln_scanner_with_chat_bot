import asyncio
import json
import os
import pathlib
import shutil
from datetime import datetime, timezone
from app.Exception.tools_exception import ToolInternalError, ToolNotFoundError
from app.executors.base import Executor
from app.models.scan_result import ScanResult

# Chemin par defaut relatif au projet (scanner/wordlists/common.txt), surchageable via env var
DEFAULT_WORDLIST = str(pathlib.Path(__file__).resolve().parents[2] / "wordlists" / "common.txt")

class FeroxbusterExecutor(Executor):

    def parse(self, stdout: bytes) -> list:
        discovered_resources = []
        raw_lines = stdout.decode().strip().split("\n")
        seen_urls = set()
        
        for line in raw_lines:
            if not line.strip():
                continue
            try:
                parsed_json = json.loads(line.strip())
                discovered_url = parsed_json.get("url", "")
                
                if discovered_url and discovered_url not in seen_urls:
                    seen_urls.add(discovered_url)
                    
                    discovered_resources.append({
                        "url": discovered_url,
                        "status_code": parsed_json.get("status", 0),
                        "content_length": parsed_json.get("content_length", 0),
                        "type": parsed_json.get("type", "unknown"), # ex: "directory" ou "file"
                        "words": parsed_json.get("word_count", 0)
                    })
            except Exception:
                pass
                
        return discovered_resources  
      
    async def excutor(self, data: dict) -> dict:
        url = data.get("url", data.get("domain", "unknown"))
        
        feroxbuster_path = shutil.which("feroxbuster")
        if feroxbuster_path is None:
            raise ToolNotFoundError("feroxbuster", "feroxbuster tool not found")

        wordlist_path = os.getenv("FEROXBUSTER_WORDLIST", DEFAULT_WORDLIST)
        if not os.path.exists(wordlist_path):
            # Correction des paramètres pour correspondre à ton ToolInternalError
            raise ToolInternalError("Feroxbuster wordlist missing", tool_name="feroxbuster", message="Wordlist not found")
    
        proc = await asyncio.create_subprocess_exec(
            feroxbuster_path, "-u", url,
            "-w", wordlist_path,
            "-g",
            "--json", "--silent",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        result = {}
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise ToolInternalError(stderr.decode(), tool_name="feroxbuster", message="Tool returned non-zero exit status.")
        
        resources = self.parse(stdout)
        
        # ! Indice crucial : Si la connexion n'a pas pu s'établir, la liste des ressources sera vide
        if not resources:
            result["feroxbuster_status"] = "failed_or_empty"
            result["feroxbuster_resources"] = []

            data["feroxbuster_result"] = result
            return data
        
        result["feroxbuster_status"] = "completed"
        result["feroxbuster_resources"] = resources

        data ["feroxbuster_result"]  = result
            
        return data