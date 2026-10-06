def define_flags():
    return {
        "flags": [
            {"name": "help", "short": "h", "long": "help", "takes_value": False}
        ],
        "aliases": {"h": "help"}
    }

def run(args, flags, user_context, stdin_data=None, **kwargs):
    if flags.get("help"):
        return {"success": True, "output": help(args, flags, user_context)}

    text = str(stdin_data) if stdin_data is not None else " ".join(args)
    return {
        "effect": "clipboard_action",
        "action": "copy",
        "text": text,
        "silent": True
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    pbcopy - Copy standard input or arguments to clipboard

SYNOPSIS
    pbcopy [text...]
    <command> | pbcopy

DESCRIPTION
    Copies data from standard input or command arguments to the system clipboard,
    matching macOS / BSD pbcopy behavior.

EXAMPLES
    cat file.txt | pbcopy
    pbcopy "fractal os"
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: pbcopy [text] (or pipe stdin to pbcopy)"
