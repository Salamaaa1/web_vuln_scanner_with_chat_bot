from __future__ import annotations
from abc import ABC, abstractmethod
import asyncio
from typing import List
from app.models.target import Target
from app.models.scan_result import ScanResult
from app.executors.base import Executor, Worker
from app.executors.factory import ExecutorFactory
from app.core import progress as progress_store





def _summarize_worker(name: str, result: dict) -> str:
    """Build a short human-readable status line for a finished tool."""
    name = name.strip()
    try:
        if name == "subfinder":
            n = len((result.get("subfinder_result", {}) or {}).get("subfinder_subdomains", []) or [])
            return f"subfinder terminé — {n} sous-domaine(s)"
        if name == "httpx":
            hx = result.get("httpx_result", [])
            n = len(hx) if isinstance(hx, list) else 0
            return f"httpx terminé — {n} hôte(s) actif(s)"
        if name == "katana":
            n = len((result.get("katana_result", {}) or {}).get("katana_endpoints", []) or [])
            return f"katana terminé — {n} endpoint(s) crawlé(s)"
        if name == "feroxbuster":
            n = len((result.get("feroxbuster_result", {}) or {}).get("feroxbuster_resources", []) or [])
            return f"feroxbuster terminé — {n} ressource(s)"
        if name == "nmap":
            n = len((result.get("nmap_result", {}) or {}).get("open_ports", []) or [])
            return f"nmap terminé — {n} port(s) ouvert(s)"
        if name == "nuclei":
            res = result.get("nuclei_result", {}) or {}
            n = len(res.get("vulnerabilities", []) or [])
            scope = ""
            if "scanned_targets" in res:
                scope = f" ({res['scanned_targets']} cible(s), {res.get('dast_targets', 0)} URL(s) à paramètres fuzzée(s))"
            if res.get("dast_error"):
                scope += " — fuzzing DAST indisponible"
            if res.get("timed_out"):
                return f"nuclei arrêté (limite de temps atteinte) — {n} vulnérabilité(s) trouvée(s){scope}"
            return f"nuclei terminé — {n} vulnérabilité(s){scope}"
    except Exception:
        pass
    return f"{name} terminé"


class Step:
    def __init__(self, workers: List[Worker]) -> None:
        self.workers = workers

    async def execute_step(self, progress=None) -> dict:

        async def _run(worker):
            if progress:
                await progress(f"{worker.executor_name.strip()} : en cours…", "info")
            result = await worker.run()
            # Update the live dashboard counters with what we have so far.
            progress_store.report_partial(result)
            if progress:
                res = result.get(f"{worker.executor_name.strip()}_result", {})
                failed = isinstance(res, dict) and res.get("status") == "failed"
                if failed:
                    await progress(f"{worker.executor_name.strip()} : échec — {res.get('error', '')}", "error")
                else:
                    await progress(_summarize_worker(worker.executor_name, result), "success")
            return result

        tasks = [asyncio.create_task(_run(worker)) for worker in self.workers]
        results = await asyncio.gather(*tasks)
        # Fusionner tous les dictionnaires de la liste 'results' en un seul
        final_dict = {}
        for d in results:
            final_dict |= d  # ou final_dict.update(d)

        return final_dict
    



# class Stage : 

#     def __init__(self, name: str) -> None:
#         self.name = name
#         self.steps = []

#     def add_step(self, step: Step) -> Stage:
#         self.steps.append(step)
#         return self
    
#     async def excute_stage(self) -> dict:
        
        
#         final_result = {}
#         for step in self.steps:
#             r = await step.execute_step()
#             final_result |= r
        
#         return final_result

class AbstractPipeline(ABC):
    def __init__(self) -> None:
        self.steps: List[Step] = []

    def add_steps(self , step: Step) -> AbstractPipeline:
        self.steps.append(step)
        return self 
    

    @abstractmethod
    def pipeline_build(self, data : dict ) :
        return 


    async def execute_pipeline(self, progress=None) -> dict:

        data_final = {}
        total = len(self.steps)
        for i, step in enumerate(self.steps, 1):
            if progress:
                tools = ", ".join(w.executor_name.strip() for w in step.workers)
                await progress(f"Étape {i}/{total} — {tools}", "info")
            data = await step.execute_step(progress=progress)
            data_final |= data

        return data_final
    
