def define_flags():
    return {
        "flags": ["help"],
        "aliases": {"h": "help"}
    }

def run(args, flags, user_context, **kwargs):
    """
    Status command - displays system tray, bar, and resource status.
    """
    if flags.get("help"):
        return {"success": True, "output": help(args, flags, user_context)}

    if not args:
        return {
            "effect": "status_action",
            "action": "summary"
        }

    subcmd = args[0].lower()

    if subcmd == "bar":
        val = None
        if len(args) > 1:
            target = args[1].lower()
            if target in ("on", "show", "enable", "true", "1"):
                val = True
            elif target in ("off", "hide", "disable", "false", "0"):
                val = False
            else:
                return {
                    "success": False,
                    "error": {
                        "message": f"status bar: invalid argument '{args[1]}'",
                        "suggestion": "Usage: status bar [on|off]"
                    }
                }
        return {
            "effect": "status_action",
            "action": "toggle_bar",
            "value": val
        }

    if subcmd in ("mute", "sound", "audio"):
        val = None
        if len(args) > 1:
            target = args[1].lower()
            if target in ("on", "mute", "true", "1"):
                val = True
            elif target in ("off", "unmute", "false", "0"):
                val = False
            else:
                return {
                    "success": False,
                    "error": {
                        "message": f"status mute: invalid argument '{args[1]}'",
                        "suggestion": "Usage: status mute [on|off]"
                    }
                }
        return {
            "effect": "status_action",
            "action": "set_mute",
            "value": val
        }

    if subcmd in ("notifications", "notif", "log", "alerts"):
        return {
            "effect": "status_action",
            "action": "list_notifications"
        }

    if subcmd in ("clear", "clean"):
        return {
            "effect": "status_action",
            "action": "clear_notifications"
        }

    return {
        "success": False,
        "error": {
            "message": f"status: unknown option '{subcmd}'",
            "suggestion": "Usage: status [bar [on|off]|mute [on|off]|notifications|clear]"
        }
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    status - System status, tray monitors, and notification status

SYNOPSIS
    status
    status bar [on|off]
    status mute [on|off]
    status notifications
    status clear

DESCRIPTION
    Displays a real-time status summary of FractalOS system components,
    including working directory, active terminal panes, background jobs,
    connected mesh peers, audio mute status, AI agent state, and recent alerts.

SUBCOMMANDS
    (none)
        Display full system status summary.
    bar [on|off]
        Toggle or set the visibility of the persistent status & notification bar.
    mute [on|off]
        Toggle or set audio sound mute state.
    notifications, notif
        List recent notifications from the notification center.
    clear
        Clear all notifications from the notification center.

EXAMPLES
    status
    status bar off
    status mute on
    status notifications
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: status [bar [on|off]|mute [on|off]|notifications|clear]"
