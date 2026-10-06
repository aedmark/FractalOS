def define_flags():
    return {
        'flags': [
            {'name': 'list', 'short': 'l', 'long': 'list', 'takes_value': False},
            {'name': 'detach', 'short': 'd', 'long': 'detach', 'takes_value': False},
        ],
        'metadata': {}
    }

def run(args, flags, user_context, config=None, **kwargs):
    if not config or not config.get('NETWORKING_ENABLED'):
        return {
            "success": False,
            "error": {
                "message": "attach: networking is disabled by the system administrator.",
                "suggestion": "To enable networking, set NETWORKING_ENABLED to true in the system configuration and reboot."
            }
        }

    is_detach = flags.get('detach', False)
    is_list = flags.get('list', False)

    if is_detach:
        return {"effect": "mesh_detach"}

    if is_list or len(args) == 0:
        return {"effect": "mesh_attach_list"}

    if len(args) == 1:
        return {
            "effect": "mesh_attach",
            "targetId": args[0]
        }

    return {
        "success": False,
        "error": {
            "message": "attach: too many arguments",
            "suggestion": "Usage: attach [-l] [-d] [<instanceId>]"
        }
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    attach - Attach to a shared terminal session across FractalOS mesh nodes.

SYNOPSIS
    attach [-l | --list]
    attach [-d | --detach]
    attach <instanceId>

DESCRIPTION
    Attach your local terminal to a remote FractalOS instance on the mesh network.
    Once attached, commands entered locally execute in the remote host's environment,
    with outputs streamed back in real time. Both host and client see commands in
    a shared pair-programming terminal session.

    To leave an attached session, type 'detach' or 'exit'.

OPTIONS
    -l, --list      List discovered nodes available for attachment.
    -d, --detach    Detach from the currently active remote session.

EXAMPLES
    attach -l
    attach oos-1727700000-42
    attach -d
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: attach [-l] [-d] [<instanceId>]"
