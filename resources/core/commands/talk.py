def run(args, flags, user_context, config=None, stdin=None, **kwargs):
    if not config or not config.get('NETWORKING_ENABLED'):
        return {
            "success": False,
            "error": {
                "message": "talk: networking is disabled by the system administrator.",
                "suggestion": "To enable networking, set NETWORKING_ENABLED to true in the system configuration and reboot."
            }
        }

    if not args:
        return {
            "success": False,
            "error": {
                "message": "talk: missing recipient instance ID",
                "suggestion": "Usage: talk <targetId> \"<message>\""
            }
        }

    target_id = args[0]
    message = " ".join(args[1:]).strip() if len(args) > 1 else ""
    if not message and stdin:
        message = stdin.strip()

    if not message:
        return {
            "success": False,
            "error": {
                "message": "talk: message cannot be empty",
                "suggestion": "Usage: talk <targetId> \"<message>\""
            }
        }

    return {
        "effect": "mesh_talk",
        "targetId": target_id,
        "message": message,
        "sender": user_context.get('name', 'Guest')
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    talk - Talk to another FractalOS node on the mesh.

SYNOPSIS
    talk <targetId> "<message>"

DESCRIPTION
    Sends a direct message to a specific FractalOS node across the mesh
    network, alerting the recipient terminal.

OPTIONS
    This command takes no options.

EXAMPLES
    talk oos-1727700000-42 "Can you review the latest commit?"
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: talk <targetId> \"<message>\""
