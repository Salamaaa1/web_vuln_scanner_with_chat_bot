from app.executors.base import Worker
from app.executors.feroxbuster import FeroxbusterExecutor
from app.executors.httpx import HttpxExecutor
from app.executors.katana import KatanaExecutor
from app.executors.nuclei import NucleiExecutor
from app.pipelines.base import AbstractPipeline, Step
from app.models.target import Target
from app.models.scan_result import ScanResult
from typing import List


class UrlPipeline(AbstractPipeline):
    """
    Pipeline for URL / Web-application targets.

    Steps :
        1. Tech Detection       — Httpx fingerprints the endpoint
                                  (status code, title, technologies)
        2. Crawling & Fuzzing   — Katana crawls the app to discover paths ;
                                  Feroxbuster brute-forces hidden directories
        3. Vulnerability Scan   — Nuclei runs OWASP templates
                                  (XSS, SQLi, misconfigs, CVEs …)
    """

    def __init__(self) -> None:
        super().__init__()
        # URL Pipeline steps:
        # 1. Tech Detect (httpx)
        # 2. Crawling & Fuzzing (katana, feroxbuster)
        # 3. Vuln Scan (nuclei)

    def  pipeline_build(self, data : dict ) :

        executorData = data.copy()

        executorData["url"] = data["url"]
        executorData["httpx_result"] = {}
        executorData["katana_result"] = {}
        executorData["feroxbuster_result"] = {}
        executorData["nuclei_result"] = {}



        htppxWorker  = Worker(HttpxExecutor(),executorData , "httpx")
        feroxbusterWorker = Worker(FeroxbusterExecutor(), executorData, "feroxbuster")
        katanaWorker = Worker(KatanaExecutor(), executorData, "katana")
        stepOne = Step(
            workers=[htppxWorker, katanaWorker, feroxbusterWorker]
            )
                
        nucleiWorker = Worker(NucleiExecutor(), executorData, "nuclei")
        stepTwo = Step(
            workers=[nucleiWorker]
            )
        

        self.add_steps(stepOne).add_steps(stepTwo)
        

        return self
        
        
   
