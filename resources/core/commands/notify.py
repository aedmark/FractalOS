def define_flags():
    return {
        "flags": ["info", "success", "warn", "error", "silent", "help"],
        "aliases": {
            "i": "info",
            "s": "silent",
            "h": "help"
        }
    }

def run(args, flags, user_context, **kwargs):
    """
    Sends a system notification to the status bar and notification center.
    """
    if flags.get("help"):
        return {"success": True, "output": help(args, flags, user_context)}

    if not args:
        return {
            "success": False,
            "error": {
                "message": "notify: missing notification message",
                "suggestion": "Usage: notify <message> [--info|--success|--warn|--error] [--silent]"
            }
        }

    subcmd = args[0].lower()
    if subcmd in ("list", "ls"):
        return {
            "effect": "status_action",
            "action": "list_notifications"
        }

    if subcmd in ("clear", "clean"):
        return {
            "effect": "status_action",
            "action": "clear_notifications"
        }

    message = " ".join(args)

    level = "info"
    if flags.get("error"):
        level = "error"
    elif flags.get("warn"):
        level = "warn"
    elif flags.get("success"):
        level = "success"

    silent = bool(flags.get("silent"))

    return {
        "effect": "notify",
        "message": message,
        "level": level,
        "silent": silent
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    notify - Send system notifications and alerts

SYNOPSIS
    notify <message> [--info|--success|--warn|--error] [--silent]
    notify list
    notify clear

DESCRIPTION
    Sends a notification alert to the FractalOS persistent status bar
    ticker and archives it into the system notification drawer.

OPTIONS
    --info
        Information notification (default, blue).
    --success
        Success notification (green checkmark).
    --warn
        Warning notification (yellow alert).
    --error
        Error alert (red critical badge).
    -s, --silent
        Do not play audio chime for notification.

SUBCOMMANDS
    list
        List recent notifications in the terminal.
    clear
        Clear all notifications from the drawer.

EXAMPLES
    notify "Build complete!" --success
    notify "Low battery or disk threshold" --warn
    notify list
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: notify <message> [--success|--warn|--error] [--silent] | notify list | notify clear"
