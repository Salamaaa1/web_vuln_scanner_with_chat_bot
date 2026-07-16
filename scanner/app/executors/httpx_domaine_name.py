import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from app.Exception.tools_exception import ToolInternalError, ToolNotFoundError
from app.executors.base import Executor
from app.executors.tool_utils import resolve_httpx
from app.models.scan_result import ScanResult

class HttpxDomaineExecutor(Executor):
    async def excutor(self, data: dict) -> dict:
        # Vérification de la présence de l'outil
        httpx_path = resolve_httpx()
        if httpx_path is None:
            raise ToolNotFoundError("httpx-toolkit", "httpx tool not found")

        # Flags de reconnaissance avancée requis
        common_flags = [
            "-status-code", "-tech-detect", "-title", "-server", 
            "-favicon", "-cname", "-cdn", "-tls-probe", 
            "-content-length", "-location", "-json", "-silent"
        ]

        # 1. Extraction des sous-domaines depuis la structure de Subfinder
        # On cible data["subfinder_result"]["subdomains"] avec un fallback de sécurité
        subfinder_res = data.get("subfinder_result", {})
        subdomains = subfinder_res.get("subfinder_subdomains", [])

        # Si la liste est vide (aucun sous-domaine trouvé), on s'arrête gentiment
        if not subdomains:
            data["httpx_result"] = []
            return data

        # 2. Création du fichier temporaire (Mode Liste)
        temp_file_path = None
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as temp_file:
            for sub in subdomains:
                temp_file.write(f"{sub}\n")
            temp_file_path = temp_file.name

        # Construction dynamique des arguments avec le flag -l
        cmd_args = [httpx_path] + common_flags + ["-l", temp_file_path]

        # 3. Exécution de la commande
        proc = await asyncio.create_subprocess_exec(
            *cmd_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        # Nettoyage immédiat du fichier temporaire du système
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass

        # Gestion des erreurs d'exécution critiques
        if proc.returncode != 0:
            raise ToolInternalError(stderr.decode(), tool_name="httpx", message="Tool returned non-zero exit status.")

        # 4. Parsing de la sortie JSONL (JSON Lines)
        results = []
        for line in stdout.decode().splitlines():
            if line.strip():
                try:
                    results.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

        # Sauvegarde des résultats dans le dictionnaire global du pipeline
        data["httpx_result"] = results
        return data