import asyncio
from typing import List, Any
from app.models.target import Target

class WorkerPool:
    def __init__(self, pool_size: int = 5) -> None:
        self.pool_size = pool_size
        self._workers: List[asyncio.Task] = []

    @property
    def pollSize(self) -> int:
        return self.pool_size

    @pollSize.setter
    def pollSize(self, value: int) -> None:
        self.pool_size = value

    async def execute_target(self, target: Target, workers: List[Any]) -> List[dict]:
        """
        WorkerPool is responsible for determining the number of threads (tasks) and creating them
        according to the number of workers to run.
        """
        # Determine the number of threads (tasks) according to the workers list size
        self.pool_size = len(workers)

        tasks = []
        for worker in workers:
            # Create asyncio tasks representing parallel threads
            task = asyncio.create_task(worker.run())
            tasks.append(task)
        
        self._workers = tasks
        
        # Run concurrently and combine results
        results = await asyncio.gather(*tasks)
        
        self._workers = []
        return results
