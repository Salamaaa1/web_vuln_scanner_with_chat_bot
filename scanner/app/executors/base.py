from abc import ABC, abstractmethod
from app.Exception.tools_exception import NoDataFoundError, ToolInternalError, ToolNotFoundError
from app.models.target import Target

class Worker:
    def __init__(self, executor: 'Executor', data: dict , excutor_name: str   ) -> None:
        self.executor = executor
        self.data = data
        self.executor_name = excutor_name

    async def run(self) -> dict:

        try: 
            self.data = await self.executor.excutor(self.data)
        # except ToolNotFoundError as e:
        #     print(f"Tool '{e.tool_name}' not found.")
        #     self.data[f'{e.tool_name}_status'] = "failed"
        #     self.data[f'{e.tool_name}_error'] = str(e)

        # except NoDataFoundError as e:
        #     print(f"No Data found to scan for Tool '{e.tool_name}' .")
        #     self.data[f'{e.tool_name}_status'] = "failed"
        #     self.data[f'{e.tool_name}_error'] = str(e)

        # except ToolInternalError as e:
        #     print(f"Tool '{e.tool_name}' not found. stderr: {e.stderr}")
        #     self.data[f'{e.tool_name}_status'] = "failed"
        #     self.data[f'{e.tool_name}_error'] = str(e)

        except Exception as e:
            import traceback
            print(f"An error occurred in {self.executor_name}: {type(e).__name__}: {e}")
            traceback.print_exc()
            self.data[f'{self.executor_name.strip()}_result']['status'] = "failed"
            self.data[f'{self.executor_name.strip()}_result']['error'] = f"{type(e).__name__}: {e}"
           
        return self.data 


class Executor(ABC):
    @abstractmethod
    async def excutor(self, data: dict) -> dict:
        """
        The abstract method to be implemented by concrete executors.
        """
        pass

   
    
    