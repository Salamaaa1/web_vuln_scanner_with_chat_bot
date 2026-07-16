from app.executors.base import Worker
from app.executors.httpx import HttpxExecutor
from app.executors.nmap import NmapExecutor
from app.executors.nuclei import NucleiExecutor
from app.pipelines.base import AbstractPipeline, Step
from app.models.target import Target
from app.models.scan_result import ScanResult
from typing import List

class MachinePipeline(AbstractPipeline):
        

    def __init__(self) -> None:
     super().__init__()
  
    def  pipeline_build(self, data : dict ) :

        executorData = data.copy()

        executorData["ip"] = data["ip"]
        executorData["nmap_result"] = {}
        executorData["httpx_result"] = {}
        executorData["nuclei_result"] = {}



        nmapWorker  = Worker(NmapExecutor(),executorData , "nmap")
       
        stepOne = Step(
            workers=[nmapWorker]
            )
        
        httppxWorker  = Worker(HttpxExecutor(), executorData, "httpx")
        stepTwo = Step(
            workers=[httppxWorker]
            )

        nucleiWorker = Worker(NucleiExecutor(), executorData, "nuclei")
        stepThree = Step(
            workers=[nucleiWorker]
            )
        
        

        self.add_steps(stepOne).add_steps(stepTwo).add_steps(stepThree)
        

        return self
        
        
   
