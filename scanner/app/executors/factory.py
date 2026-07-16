from typing import List, Dict, Type
from app.executors.base import Executor
from app.executors.httpx import HttpxExecutor
from app.executors.nmap import NmapExecutor
from app.executors.nuclei import NucleiExecutor
from app.executors.feroxbuster import FeroxbusterExecutor
from app.executors.katana import KatanaExecutor

class ExecutorFactory:
    _executors: Dict[str, Type[Executor]] = {
        "httpx": HttpxExecutor,
        "nmap": NmapExecutor,
        "nuclei": NucleiExecutor,
        "feroxbuster": FeroxbusterExecutor,
        "katana": KatanaExecutor,
    }

    @classmethod
    def create_executor(cls, tool_name: str) -> Executor:
        """
        Instantiate a specific executor from its tool name.
        """
        executor_class = cls._executors.get(tool_name.lower())
        if not executor_class:
            raise ValueError(f"Unknown executor: {tool_name}")
        return executor_class()

    @classmethod
    def create_executors(cls, tool_names: List[str]) -> List[Executor]:
        """
        Instantiate multiple executors. (Corresponds to createExcutor():List<Executor> in UML)
        """
        return [cls.create_executor(name) for name in tool_names]
