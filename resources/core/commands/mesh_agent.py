"""
mesh_agent.py - Delegate tasks and queries to peer AI agents across the FractalOS mesh network.
"""

def define_flags():
    return {
        "flags": ["--autopilot", "-a", "--timeout", "-t", "--json", "-j", "--help", "-h"],
        "metadata": {
            "--timeout": {"type": "integer"},
            "-t": {"type": "integer"}
        }
    }

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    if not args or len(args) < 2:
        return {
            "success": False,
            "error": {
                "message": "mesh-agent: missing target peer ID or prompt",
                "suggestion": "Usage: mesh-agent <nodeId> <prompt> [--autopilot] [--timeout <sec>]"
            }
        }

    target = str(args[0]).strip()
    prompt = " ".join(str(a) for a in args[1:]).strip()

    if not target:
        return {
            "success": False,
            "error": {
                "message": "mesh-agent: invalid target node ID",
                "suggestion": "Specify a discovered node ID (run 'peers' to view available nodes)."
            }
        }

    if not prompt:
        return {
            "success": False,
            "error": {
                "message": "mesh-agent: empty prompt",
                "suggestion": "Provide a question or task for the remote agent."
            }
        }

    is_autopilot = "--autopilot" in flags or "-a" in flags
    as_json = "--json" in flags or "-j" in flags

    timeout = 30
    if "--timeout" in flags:
        try:
            timeout = int(flags["--timeout"])
        except (ValueError, TypeError):
            pass
    elif "-t" in flags:
        try:
            timeout = int(flags["-t"])
        except (ValueError, TypeError):
            pass

    return {
        "effect": "mesh_agent_delegate",
        "target": target,
        "prompt": prompt,
        "isAutopilot": is_autopilot,
        "timeout": timeout,
        "asJson": as_json
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    mesh-agent - delegate tasks and queries to remote peer agents over the mesh network

SYNOPSIS
    mesh-agent <nodeId> <prompt> [--autopilot|-a] [--timeout|-t <sec>] [--json|-j]

DESCRIPTION
    Dispatches sub-tasks, queries, or autopilot operations to a peer node's 'samwise'
    agent across the FractalOS distributed mesh network (via WebSockets, WebRTC, or
    BroadcastChannel).

    The remote agent executes the task in its own local environment, with access to its
    local file system, hardware GPIO sensors, and shell environment, then transmits back
    the synthesized answer or autopilot execution log.

OPTIONS
    --autopilot, -a
        Executes the delegated prompt using BoneAmanita Autopilot mode on the remote node.
    --timeout, -t <sec>
        Maximum seconds to wait for remote completion (default: 30s).
    --json, -j
        Output the raw structured JSON response from the remote peer.

EXAMPLES
    mesh-agent node-beta "What is your system hostname and uptime?"
        Sends a read query to peer node-beta and prints synthesized response.

    mesh-agent node-beta "gpio read 17"
        Asks node-beta's agent to inspect its local hardware pin 17.

    mesh-agent node-beta "Turn on LED pin 18" -a
        Instructs peer node-beta to run autopilot to actuate its local hardware.

SEE ALSO
    peers, samwise, attach, mesh-cp
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: mesh-agent <nodeId> <prompt> [--autopilot] [--timeout <sec>] [--json]"
