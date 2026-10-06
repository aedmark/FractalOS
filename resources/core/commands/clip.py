def define_flags():
    return {
        "flags": [
            {"name": "copy", "short": "c", "long": "copy", "takes_value": False},
            {"name": "paste", "short": "p", "long": "paste", "takes_value": False},
            {"name": "clear", "short": "x", "long": "clear", "takes_value": False},
            {"name": "status", "short": "s", "long": "status", "takes_value": False},
            {"name": "help", "short": "h", "long": "help", "takes_value": False},
        ],
        "aliases": {
            "c": "copy",
            "p": "paste",
            "x": "clear",
            "s": "status",
            "h": "help"
        }
    }

def run(args, flags, user_context, stdin_data=None, **kwargs):
    if flags.get("help"):
        return {"success": True, "output": help(args, flags, user_context)}

    # If --clear flag
    if flags.get("clear"):
        return {"effect": "clipboard_action", "action": "clear"}

    # If --paste flag
    if flags.get("paste"):
        return {"effect": "clipboard_action", "action": "paste"}

    # If --copy flag
    if flags.get("copy"):
        text = " ".join(args) if args else (str(stdin_data) if stdin_data is not None else "")
        return {"effect": "clipboard_action", "action": "copy", "text": text}

    # If --status flag
    if flags.get("status"):
        return {"effect": "clipboard_action", "action": "status"}

    # If stdin is provided and no args
    if not args:
        if stdin_data is not None:
            return {"effect": "clipboard_action", "action": "copy", "text": str(stdin_data)}
        return {"effect": "clipboard_action", "action": "status"}

    subcmd = args[0].lower()

    if subcmd in ("copy", "cp", "set", "c"):
        text = " ".join(args[1:]) if len(args) > 1 else (str(stdin_data) if stdin_data is not None else "")
        return {"effect": "clipboard_action", "action": "copy", "text": text}

    if subcmd in ("paste", "get", "p"):
        return {"effect": "clipboard_action", "action": "paste"}

    if subcmd in ("clear", "clr", "reset"):
        return {"effect": "clipboard_action", "action": "clear"}

    if subcmd in ("status", "info", "stat"):
        return {"effect": "clipboard_action", "action": "status"}

    # If user just typed: clip <text...> without subcmd, treat as copy
    text = " ".join(args)
    return {"effect": "clipboard_action", "action": "copy", "text": text}

def man(args, flags, user_context, **kwargs):
    return """
NAME
    clip - Clipboard bridge between host OS and FractalOS shell

SYNOPSIS
    clip [copy <text> | paste | clear | status]
    clip [-c | -p | -x | -s]
    <command> | clip

DESCRIPTION
    Interacts with the system clipboard. Allows copying text to clipboard,
    pasting from clipboard, checking status, and piping shell output into clipboard.

SUBCOMMANDS
    copy <text>, -c
        Copy argument text or standard input into the clipboard.
    paste, -p
        Retrieve and output clipboard content.
    clear, -x
        Clear clipboard content.
    status, -s
        Display clipboard buffer metadata.

EXAMPLES
    clip copy Hello World
    echo "Piped text" | clip
    clip paste
    clip clear
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: clip [copy <text> | paste | clear | status] (or pipe stdin to clip)"
