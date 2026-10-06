def run(args, flags, user_context, config=None, **kwargs):
    if args:
        return {
            "success": False,
            "error": {
                "message": "detach: command takes no arguments",
                "suggestion": "Usage: detach"
            }
        }

    return {"effect": "mesh_detach"}

def man(args, flags, user_context, **kwargs):
    return """
NAME
    detach - Detach from an active remote FractalOS terminal session.

SYNOPSIS
    detach

DESCRIPTION
    Leaves the currently attached remote mesh terminal session and returns
    to the local terminal shell prompt.

OPTIONS
    This command takes no options.

EXAMPLES
    detach
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: detach"
