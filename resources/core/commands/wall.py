def run(args, flags, user_context, config=None, stdin=None, **kwargs):
    if not config or not config.get('NETWORKING_ENABLED'):
        return {
            "success": False,
            "error": {
                "message": "wall: networking is disabled by the system administrator.",
                "suggestion": "To enable networking, set NETWORKING_ENABLED to true in the system configuration and reboot."
            }
        }

    message = " ".join(args).strip() if args else ""
    if not message and stdin:
        message = stdin.strip()

    if not message:
        return {
            "success": False,
            "error": {
                "message": "wall: no message provided",
                "suggestion": "Usage: wall <message> or echo \"<message>\" | wall"
            }
        }

    return {
        "effect": "mesh_wall",
        "message": message,
        "sender": user_context.get('name', 'Guest')
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    wall - Write a broadcast message to all terminals on the mesh.

SYNOPSIS
    wall <message>
    <command> | wall

DESCRIPTION
    Displays a broadcast message across the terminals of all connected
    FractalOS mesh nodes. Reads from arguments or standard input.

OPTIONS
    This command takes no options.

EXAMPLES
    wall System maintenance in 5 minutes.
    echo "Server rebooting" | wall
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: wall <message>"
