class ToolNotFoundError(Exception):

    def __init__(self, tool_name: str, message: str | None = None):
        self.tool_name = tool_name
        super().__init__(message or f"Tool '{tool_name}' not found.")


class ToolInternalError(Exception):

    def __init__(self, stderr:str ,  tool_name: str, message: str | None = None):
        self.tool_name = tool_name
        self.stderr = stderr
        super().__init__(message or f"Tool '{tool_name}' not found. stderr: {stderr}")


class NoDataFoundError(Exception):

    def __init__(self,  tool_name: str, message: str | None = None):
        self.tool_name = tool_name
       
        super().__init__(message or f"No Data found to scan for Tool '{tool_name}' .")