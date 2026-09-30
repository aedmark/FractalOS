from executor import command_executor
from filesystem import fs_manager
from session import env_manager, history_manager, alias_manager, session_manager
from groups import group_manager
from users import user_manager
from sudo import SudoManager
from ai_manager import AIManager
from story_manager import story_manager
from apps.editor import editor_manager
from apps.paint import paint_manager
from apps.adventure import adventure_manager
from apps import top as top_app
from apps import log as log_app
from apps import basic as basic_app
from audit import audit_manager
import json
import traceback
import inspect
import asyncio

sudo_manager = SudoManager(fs_manager)
ai_manager = AIManager(fs_manager, command_executor)
command_executor.set_ai_manager(ai_manager)

MODULE_DISPATCHER = {
    "executor": command_executor, "filesystem": fs_manager, "session": session_manager,
    "env": env_manager, "history": history_manager, "alias": alias_manager,
    "groups": group_manager, "users": user_manager, "sudo": sudo_manager, "ai": ai_manager,
    "story": story_manager,
    "editor": editor_manager, "paint": paint_manager,
    "adventure": adventure_manager, "top": top_app, "log": log_app, "basic": basic_app, "audit": audit_manager
}

def initialize_kernel(save_function):
    fs_manager.set_save_function(save_function)

async def syscall_handler(request_json):
    """
    The single, now ASYNC, entry point for all calls from the JavaScript frontend.
    """
    try:
        request = json.loads(request_json)
        module_name = request.get("module")
        function_name = request.get("function")
        args = request.get("args", [])
        kwargs = request.get("kwargs", {})

        if module_name not in MODULE_DISPATCHER:
            raise ValueError(f"Unknown module: {module_name}")

        manager = MODULE_DISPATCHER[module_name]
        target_func = getattr(manager, function_name)

        if inspect.iscoroutinefunction(target_func):
            result = await target_func(*args, **kwargs)
        else:
            result = target_func(*args, **kwargs)

        if inspect.isawaitable(result):
            result = await result

        if isinstance(result, dict) and 'success' in result:
            return json.dumps(result)
        if isinstance(result, str):
            try:
                json.loads(result)
                return result
            except json.JSONDecodeError: pass
        return json.dumps({"success": True, "data": result})

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Kernel Dispatch Error in {module_name}.{function_name}: {repr(e)}",
            "traceback": traceback.format_exc()
        })

try:
    from pyodide.ffi import jsnull as _JS_NULL
except ImportError:
    _JS_NULL = None


def _from_js(value):
    """JS null crosses the bridge as pyodide.ffi.jsnull, which is not None (and
    is falsy but has no str methods). Commands test `stdin_data is not None`, so
    normalise it here, at the one entry point, rather than in 123 commands."""
    if _JS_NULL is not None and value is _JS_NULL:
        return None
    return value


async def execute_command(command_string: str, js_context_json: str, stdin_data: str = None, signal=None) -> str:
    try:
        return await command_executor.execute(command_string, js_context_json, _from_js(stdin_data), signal)
    except Exception as e:
        return json.dumps({
            "success": False, "error": f"Kernel Error before execution: {repr(e)}",
            "traceback": traceback.format_exc()
        })

