def define_flags():
    return {
        "flags": [
            {"name": "help", "short": "h", "long": "help", "takes_value": False}
        ],
        "aliases": {"h": "help"}
    }

def run(args, flags, user_context, **kwargs):
    if flags.get("help"):
        return {"success": True, "output": help(args, flags, user_context)}

    return {
        "effect": "clipboard_action",
        "action": "paste"
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    pbpaste - Print clipboard content to standard output

SYNOPSIS
    pbpaste

DESCRIPTION
    Outputs the contents of the system clipboard to standard output,
    matching macOS / BSD pbpaste behavior.

EXAMPLES
    pbpaste
    pbpaste > pasted.txt
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: pbpaste"
