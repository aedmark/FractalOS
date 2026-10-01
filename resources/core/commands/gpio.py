from host_api import host_api

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    """
    Control Raspberry Pi GPIO pins via the host sysfs or gpio utility.
    """
    if not args:
        return {
            "success": False,
            "error": {
                "message": "gpio: missing arguments",
                "suggestion": "Usage: gpio mode <pin> <in|out> | gpio read <pin> | gpio write <pin> <0|1>"
            }
        }
        
    cmd = args[0]
    
    # We will use the standard Linux `raspi-gpio` or `gpio` (wiringpi) or sysfs.
    # We can write a quick wrapper.
    if cmd == "mode":
        if len(args) != 3:
            return {"success": False, "error": {"message": "gpio mode: requires pin and mode (in/out)"}}
        pin = args[1]
        mode = args[2]
        if mode not in ("in", "out", "op", "ip"):
            return {"success": False, "error": {"message": f"gpio mode: unknown mode '{mode}'"}}
            
        res = await host_api.exec_command(f"gpio mode {pin} {mode}")
        if not res["success"]:
            return {"success": False, "error": {"message": "Host command failed.", "suggestion": res.get("error", "Unknown")}}
        if res.get("exitCode") != 0:
            return {"success": False, "error": {"message": res.get("stderr", "Unknown error")}}
            
        return res.get("stdout", "")
        
    elif cmd == "read":
        if len(args) != 2:
            return {"success": False, "error": {"message": "gpio read: requires pin"}}
        pin = args[1]
        
        res = await host_api.exec_command(f"gpio read {pin}")
        if not res["success"]:
            return {"success": False, "error": {"message": "Host command failed.", "suggestion": res.get("error", "Unknown")}}
        if res.get("exitCode") != 0:
            return {"success": False, "error": {"message": res.get("stderr", "Unknown error")}}
            
        return res.get("stdout", "")
        
    elif cmd == "write":
        if len(args) != 3:
            return {"success": False, "error": {"message": "gpio write: requires pin and value (0/1)"}}
        pin = args[1]
        val = args[2]
        
        res = await host_api.exec_command(f"gpio write {pin} {val}")
        if not res["success"]:
            return {"success": False, "error": {"message": "Host command failed.", "suggestion": res.get("error", "Unknown")}}
        if res.get("exitCode") != 0:
            return {"success": False, "error": {"message": res.get("stderr", "Unknown error")}}
            
        return res.get("stdout", "")
        
    else:
        return {"success": False, "error": {"message": f"gpio: unknown command '{cmd}'"}}

def man(args, flags, user_context, **kwargs):
    return """
NAME
    gpio - interact with physical GPIO pins

SYNOPSIS
    gpio mode <pin> <in|out>
    gpio read <pin>
    gpio write <pin> <0|1>

DESCRIPTION
    Uses the host OS bridge in Portable Mode to execute physical GPIO commands.
    Requires the `gpio` command-line utility (from wiringpi or similar) to be installed
    on the host Raspberry Pi.
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: gpio [mode|read|write] <pin> [value]"
