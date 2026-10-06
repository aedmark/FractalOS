"""
swarm.py - Mesh Swarm Management & Safety Policy Control for FractalOS.
Provides unified overview of mesh peer agents, voltage safety policies,
and swarm audit logs.
"""

def define_flags():
    return {
        "flags": [
            "--autopilot", "-a",
            "--max-voltage", "-v", "-V",
            "--dry-run",
            "--force", "-f",
            "--json", "-j",
            "--timeout", "-t",
            "--help", "-h"
        ],
        "metadata": {
            "--max-voltage": {"type": "float"},
            "-v": {"type": "float"},
            "-V": {"type": "float"},
            "--timeout": {"type": "integer"},
            "-t": {"type": "integer"}
        }
    }

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    subcmd = str(args[0]).strip().lower() if args else "status"

    if subcmd in {"status", "info"}:
        from swarm_manager import swarm_manager
        policy = swarm_manager.get_policy()
        lines = [
            "\x1b[1;35m🐝 FractalOS Swarm Status & Safety Interlocks\x1b[0m",
            "─────────────────────────────────────────────────────────────",
            f"  Max Remote Voltage Budget: \x1b[1;33m{policy.get('max_remote_voltage')} V\x1b[0m",
            f"  Remote Autopilot Allowed:  \x1b[1m{policy.get('allow_remote_autopilot')}\x1b[0m",
            f"  Hardware GPIO Actuation:   \x1b[1m{policy.get('allow_remote_gpio')}\x1b[0m {'(Prohibited)' if not policy.get('allow_remote_gpio') else '(Permitted)'}",
            f"  Remote Force Overrides:    \x1b[1m{policy.get('allow_remote_force')}\x1b[0m {'(Blocked)' if not policy.get('allow_remote_force') else '(Allowed)'}",
            f"  Provenance Auditing:       \x1b[1m{policy.get('audit_remote_tasks')}\x1b[0m (/var/log/audit.log)",
            "─────────────────────────────────────────────────────────────",
            "Subcommands:",
            "  swarm policy [set <key> <val> | reset]  - View or configure swarm safety",
            "  swarm log [limit]                       - Inspect mesh provenance audit log",
            "  swarm run <nodeId> <prompt>             - Delegate task to peer agent",
            "  peers                                   - View live discovered mesh nodes"
        ]
        return {"success": True, "output": "\n".join(lines)}

    if subcmd == "policy":
        from swarm_manager import swarm_manager
        if len(args) == 1:
            policy = swarm_manager.get_policy()
            lines = [
                "\x1b[1;36m=== Swarm Safety & Voltage Policy (/etc/swarm.conf) ===\x1b[0m",
                f"  max_remote_voltage:      \x1b[1;33m{policy.get('max_remote_voltage')} V\x1b[0m",
                f"  allow_remote_autopilot:  \x1b[1m{policy.get('allow_remote_autopilot')}\x1b[0m",
                f"  allow_remote_gpio:       \x1b[1m{policy.get('allow_remote_gpio')}\x1b[0m {'(Hardware actuation prohibited)' if not policy.get('allow_remote_gpio') else '(Hardware actuation permitted)'}",
                f"  allow_remote_force:      \x1b[1m{policy.get('allow_remote_force')}\x1b[0m {'(Remote force overrides blocked)' if not policy.get('allow_remote_force') else '(Remote force overrides allowed)'}",
                f"  audit_remote_tasks:      \x1b[1m{policy.get('audit_remote_tasks')}\x1b[0m",
                "",
                "Commands: swarm policy set <key> <value> | swarm policy reset"
            ]
            return {"success": True, "output": "\n".join(lines)}
        if args[1].lower() == "reset":
            res = swarm_manager.reset_policy(user_context)
            if res.get("success"):
                return {"success": True, "output": "\x1b[1;32mSwarm safety policy reset to factory defaults.\x1b[0m"}
            return {"success": False, "error": {"message": res.get("error", "Failed to reset policy")}}
        if args[1].lower() == "set":
            if len(args) < 4:
                return {
                    "success": False,
                    "error": {
                        "message": "Usage: swarm policy set <key> <value>",
                        "suggestion": "Example: swarm policy set allow_remote_gpio true"
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

    if subcmd in {"run", "delegate"}:
        if len(args) < 3:
            return {
                "success": False,
                "error": {
                    "message": "Usage: swarm run <nodeId> <prompt> [--autopilot] [--max-voltage <v>] [--dry-run]",
                    "suggestion": "Example: swarm run node-beta 'What is your uptime?'"
                }
            }
        # Delegate using mesh_agent handler
        from commands import mesh_agent
        return await mesh_agent.run(args[1:], flags, user_context, stdin_data, **kwargs)

    return {
        "success": False,
        "error": {
            "message": f"swarm: unknown subcommand '{subcmd}'",
            "suggestion": "Usage: swarm [status | policy | log | run <nodeId> <prompt>]"
        }
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    swarm - manage mesh swarm safety policies, peer agent delegations, and audit logs

SYNOPSIS
    swarm [status]
    swarm policy [set <key> <value> | reset]
    swarm log [limit]
    swarm run <nodeId> <prompt> [OPTIONS]

DESCRIPTION
    The swarm command provides a high-level cockpit for multi-agent swarm operations across
    the FractalOS distributed mesh. It allows node operators to inspect and configure the
    node's voltage limits, physical hardware GPIO permissions, and provenance audit log.

SUBCOMMANDS
    status
        Displays current swarm status, voltage thresholds, and safety policies.
    policy
        Displays or edits the swarm safety policy stored in /etc/swarm.conf.
    log [limit]
        Displays recent inter-node swarm delegations and executions from /var/log/audit.log.
    run <nodeId> <prompt>
        Dispatches a task to a peer agent (alias for mesh-agent).

EXAMPLES
    swarm status
        Shows summary of mesh safety settings.

    swarm policy set max_remote_voltage 15.0
        Increases the maximum voltage permitted for incoming remote autopilot tasks.

    swarm policy set allow_remote_gpio true
        Permits remote peer agents to interact with local hardware pins.

    swarm log 10
        Shows the last 10 swarm executions with node provenance and voltage ratings.

SEE ALSO
    mesh-agent, peers, samwise, gpio, attach
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: swarm [status | policy | log | run <nodeId> <prompt>]"
