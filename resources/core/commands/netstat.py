"""
netstat.py - Shows network status, connections, and mesh presence.
"""

def define_flags():
    return {
        "flags": ["--mesh", "-m", "--gui", "-g", "--all", "-a", "--ping", "-p"],
        "metadata": {}
    }

def run(args, flags, user_context, config=None, **kwargs):
    if not config or not config.get('NETWORKING_ENABLED'):
        return {
            "success": False,
            "error": {
                "message": "netstat: networking is disabled by the system administrator.",
                "suggestion": "To enable networking, set NETWORKING_ENABLED to true in the system configuration and reboot."
            }
        }

    if "--gui" in flags or "-g" in flags:
        return {
            "effect": "launch_app",
            "app_name": "Peers",
            "options": {}
        }

    if "--mesh" in flags or "-m" in flags:
        do_ping = "--ping" in flags or "-p" in flags
        return {
            "effect": "peers_display",
            "doPing": do_ping,
            "asJson": False
        }

    if args:
        sub = args[0].lower()
        if sub in ("mesh", "peers"):
            return {
                "effect": "peers_display",
                "doPing": "--ping" in flags or "-p" in flags,
                "asJson": False
            }
        return {"success": False, "error": f"netstat: unknown argument '{args[0]}'", "suggestion": "Usage: netstat [--mesh] [--gui]"}

    return {"effect": "netstat_display"}

def man(args, flags, user_context, **kwargs):
    return """
NAME
    netstat - Shows network status, connections, and mesh presence.

SYNOPSIS
    netstat [--mesh | -m] [--gui | -g] [--ping | -p]

DESCRIPTION
    Displays a list of all discovered FractalOS instances and their
    connection status, including your own instance ID.
    When given --mesh, prints detailed mesh node presence with latency
    and shared capabilities.

OPTIONS
    --mesh, -m
        Displays full mesh node presence table with latency and capabilities.
    --ping, -p
        Measures round-trip ping latency to each peer.
    --gui, -g
        Launches the graphical Mesh Network Monitor app.

EXAMPLES
    netstat
        Shows local instance ID and basic peer list.
    netstat --mesh
        Shows rich mesh node presence table.
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: netstat [--mesh | -m] [--gui | -g] [--ping | -p]"