from app.executors.base import Worker
from app.executors.httpx_domaine_name import HttpxDomaineExecutor
from app.executors.subfinder import SubfinderExecutor
from app.pipelines.base import AbstractPipeline, Step
from app.models.target import Target
from app.models.scan_result import ScanResult
from typing import List


class DnsPipeline(AbstractPipeline):
    """
    Pipeline for DNS / Domain targets.

    Steps :
        1. Passive Enumeration  — Subfinder discovers subdomains passively
        2. Active Filtering     — Httpx probes each subdomain to confirm
                                  it hosts a live HTTP service
    """

    
    def  pipeline_build(self, data : dict ) :

        executorData = data.copy()

        #!  je doit ajouter ici la verification du presence du donne
        executorData["domain"] = data["domain"]
        executorData["subfinder_result"] = {}
      



        subfinderWorker  = Worker(SubfinderExecutor(),executorData , "subfinder")
    
        stepOne = Step(
            workers=[subfinderWorker]
            )
        
        httpxWorker  = Worker(HttpxDomaineExecutor(), executorData, "httpx")
               
        stepTwo = Step(
            workers=[httpxWorker]
            )
        
       

        self.add_steps(stepOne).add_steps(stepTwo)
        

        return self
        
        
   
