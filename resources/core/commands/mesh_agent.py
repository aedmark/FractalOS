"""
mesh_agent.py - Delegate tasks and queries to peer AI agents across the FractalOS mesh network.
Supports voltage budgeting, GPIO safety interlocks, and policy inspection.
"""

def define_flags():
    return {
        "flags": [
            "--autopilot", "-a",
            "--max-voltage", "-v", "-V",
            "--dry-run",
            "--force", "-f",
            "--timeout", "-t",
            "--json", "-j",
            "--help", "-h"
        ],
        "metadata": {
            "--timeout": {"type": "integer"},
            "-t": {"type": "integer"},
            "--max-voltage": {"type": "float"},
            "-v": {"type": "float"},
            "-V": {"type": "float"}
        }
    }

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    if not args:
        return {
            "success": False,
            "error": {
                "message": "mesh-agent: missing target peer ID or subcommand",
                "suggestion": "Usage: mesh-agent <nodeId> <prompt> [--autopilot] [--max-voltage <v>] [--dry-run] | mesh-agent policy"
            }
        }

    # Handle subcommands: policy, log
    subcmd = str(args[0]).strip().lower()
    if subcmd == "policy":
        from swarm_manager import swarm_manager
        if len(args) == 1:
            policy = swarm_manager.get_policy()
            lines = [
                "\x1b[1;36m=== FractalOS Swarm Safety & Voltage Policy (/etc/swarm.conf) ===\x1b[0m",
                f"  max_remote_voltage:      \x1b[1;33m{policy.get('max_remote_voltage')} V\x1b[0m",
                f"  allow_remote_autopilot:  \x1b[1m{policy.get('allow_remote_autopilot')}\x1b[0m",
                f"  allow_remote_gpio:       \x1b[1m{policy.get('allow_remote_gpio')}\x1b[0m {'(Actuation Prohibited)' if not policy.get('allow_remote_gpio') else '(Actuation Allowed)'}",
                f"  allow_remote_force:      \x1b[1m{policy.get('allow_remote_force')}\x1b[0m {'(Overrides Blocked)' if not policy.get('allow_remote_force') else '(Overrides Allowed)'}",
                f"  audit_remote_tasks:      \x1b[1m{policy.get('audit_remote_tasks')}\x1b[0m",
                "",
                "Commands: mesh-agent policy set <key> <value> | mesh-agent policy reset"
            ]
            return {"success": True, "output": "\n".join(lines)}
        if args[1].lower() == "reset":
            res = swarm_manager.reset_policy(user_context)
            if res.get("success"):
                return {"success": True, "output": "\x1b[1;32mSwarm safety policy reset to default settings.\x1b[0m"}
            return {"success": False, "error": {"message": res.get("error", "Failed to reset policy")}}
        if args[1].lower() == "set":
            if len(args) < 4:
                return {
                    "success": False,
                    "error": {
                        "message": "Usage: mesh-agent policy set <key> <value>",
                        "suggestion": "Example: mesh-agent policy set max_remote_voltage 15.0"
                    }
                }
            key, val = args[2], args[3]
            res = swarm_manager.set_policy_value(key, val, user_context)
            if res.get("success"):
                return {"success": True, "output": f"\x1b[1;32mUpdated swarm policy:\x1b[0m {key} = {res['updated'][key]}"}
            return {"success": False, "error": {"message": res.get("error", "Failed to update policy")}}
        return {"success": False, "error": {"message": f"Unknown policy action: '{args[1]}'"}}

    if subcmd == "log":
        from audit import audit_manager
        limit = 20
        if len(args) > 1:
            try:
                limit = int(args[1])
            except (ValueError, TypeError):
                pass
        entries = audit_manager.get_swarm_entries(limit)
        if not entries:
            return {"success": True, "output": "No swarm audit log entries recorded yet in /var/log/audit.log."}
        lines = [
            f"\x1b[1;36m=== Recent Swarm Audit Events ({len(entries)}) ===\x1b[0m",
            *entries
        ]
        return {"success": True, "output": "\n".join(lines)}

    if len(args) < 2:
        return {
            "success": False,
            "error": {
                "message": "mesh-agent: missing prompt for target peer",
                "suggestion": "Usage: mesh-agent <nodeId> <prompt> [--autopilot] [--max-voltage <v>]"
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
    is_dry_run = "--dry-run" in flags
    is_force = "--force" in flags or "-f" in flags
    as_json = "--json" in flags or "-j" in flags

    max_voltage = None
    for vf in ["--max-voltage", "-v", "-V"]:
        if vf in flags:
            try:
                max_voltage = float(flags[vf])
                break
            except (ValueError, TypeError):
                pass

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
        "maxVoltage": max_voltage,
        "isDryRun": is_dry_run,
        "isForce": is_force,
        "timeout": timeout,
        "asJson": as_json
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    mesh-agent - delegate tasks and queries to remote peer agents over the mesh network

SYNOPSIS
    mesh-agent <nodeId> <prompt> [OPTIONS]
    mesh-agent policy [set <key> <value> | reset]
    mesh-agent log [limit]

DESCRIPTION
    Dispatches sub-tasks, queries, or autopilot operations to a peer node's 'samwise'
    agent across the FractalOS distributed mesh network (via WebSockets, WebRTC, or
    BroadcastChannel).

    Remote task execution is strictly governed by Swarm Voltage Policies (/etc/swarm.conf)
    enforcing maximum voltage budgets, hardware GPIO safety interlocks, and node-provenance
    audit logging in /var/log/audit.log.

OPTIONS
    --autopilot, -a
        Executes the delegated prompt using BoneAmanita Autopilot mode on the remote node.
    --max-voltage, -v, -V <voltage>
        Specifies a strict voltage budget cap for the task. If remote planning exceeds
        this limit, the task will disengage without executing kinetic actions.
    --dry-run
        Generates and scores the remote plan with voltage audit, but does not execute
        any kinetic steps.
    --force, -f
        Requests force override for High Voltage steps (only granted if target node policy
        permits remote force).
    --timeout, -t <sec>
        Maximum seconds to wait for remote completion (default: 30s).
    --json, -j
        Output the raw structured JSON response from the remote peer.

SUBCOMMANDS
    policy
        Displays the local node's swarm safety and voltage policy (/etc/swarm.conf).
    policy set <key> <value>
        Updates a policy setting (e.g. max_remote_voltage, allow_remote_gpio).
    policy reset
        Resets swarm policy to default factory settings.
    log [limit]
        Displays recent swarm events and delegated actions from /var/log/audit.log.

EXAMPLES
    mesh-agent node-beta "What is your system hostname and uptime?"
        Sends a read query to peer node-beta.

    mesh-agent node-beta "Turn on LED pin 18" -a -v 5.0
        Instructs peer to actuate LED with a 5.0 V budget cap.

    mesh-agent node-beta "Inspect temperature sensor" -a --dry-run
        Audits remote plan without running kinetic commands.

    mesh-agent policy set max_remote_voltage 15.0
        Allows remote tasks up to 15.0 V on this node.

SEE ALSO
    swarm, peers, samwise, gpio, attach
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: mesh-agent <nodeId> <prompt> [--autopilot] [--max-voltage <v>] [--dry-run] | mesh-agent policy"
