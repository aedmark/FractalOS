import json
import inspect

class HostAPI:
    def __init__(self):
        self.exec_host_func = None

    def set_exec_callback(self, func):
        self.exec_host_func = func

    async def exec_command(self, command):
        if not self.exec_host_func:
            return {"success": False, "error": "Host execution callback is not set."}
            
        result = self.exec_host_func(command)
        if inspect.isawaitable(result):
            result = await result
            
        return json.loads(result)

host_api = HostAPI()
