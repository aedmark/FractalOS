"""
peers.py - Discovers, lists, and inspects nodes on the FractalOS mesh network.
"""

def define_flags():
    return {
        "flags": ["--ping", "-p", "--json", "-j", "--gui", "-g", "--watch", "-w", "--help", "-h", "--dock", "-d", "--float", "-f", "--full"],
        "metadata": {}
    }

def run(args, flags, user_context, **kwargs):
    do_ping = "--ping" in flags or "-p" in flags
    as_json = "--json" in flags or "-j" in flags
    wants_gui = "--gui" in flags or "-g" in flags or (args and args[0].lower() in ("gui", "app", "ui"))

    if wants_gui:
        window_mode = "floating"
        if "--dock" in flags or "-d" in flags:
            window_mode = "docked-right"
        elif "--full" in flags:
            window_mode = "fullscreen"
        elif "--float" in flags or "-f" in flags:
            window_mode = "floating"

        return {
            "effect": "launch_app",
            "app_name": "Peers",
            "options": {
                "doPing": do_ping,
                "windowMode": window_mode
            }
        }

    if args:
        subcmd = args[0].lower()
        if subcmd in ("info", "inspect", "show"):
            if len(args) < 2:
                return {
                    "success": False,
                    "error": {
                        "message": "peers info: missing node ID",
                        "suggestion": "Usage: peers info <node-id>"
                    }
                }
            target_node = args[1]
            return {
                "effect": "peers_info",
                "targetId": target_node,
                "asJson": as_json
            }
        elif subcmd in ("ping", "p"):
            do_ping = True
        elif subcmd in ("list", "ls"):
            pass
        elif subcmd not in ("gui", "app", "ui"):
            # Could be a direct node query
            target_node = args[0]
            return {
                "effect": "peers_info",
                "targetId": target_node,
                "asJson": as_json
            }

    return {
        "effect": "peers_display",
        "doPing": do_ping,
        "asJson": as_json
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    peers - Mesh node presence, discovery, and capability inspector

SYNOPSIS
    peers [--ping | -p] [--json | -j] [--gui | -g]
    peers info <node-id>
    peers ping

DESCRIPTION
    Displays active peer nodes discovered on the FractalOS mesh network.
    Shows node IDs, remote usernames, transport layers (WebRTC, BroadcastChannel,
    WebSocket), round-trip ping latency, and shared capabilities (remote shell,
    p2p file transfer, multiplayer gaming).

OPTIONS
    --ping, -p
        Actively ping all discovered nodes and display round-trip latency in ms.
    --json, -j
        Output raw JSON data for shell scripting and automation.
    --gui, -g
        Launch the interactive fullscreen Mesh Network Monitor TUI app.

EXAMPLES
    peers
        Lists all discovered mesh peers.
    peers -p
        Measures latency to all peers.
    peers info oos-17913015-42
        Inspects details, capabilities, and connection status of a specific peer.
    peers --gui
        Opens the live graphical network monitor.
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: peers [--ping | -p] [--json | -j] [--gui | -g] [info <node-id>]"
