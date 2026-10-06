def define_flags():
    return {
        "flags": ["help"],
        "aliases": {"h": "help"}
    }

def run(args, flags, user_context, **kwargs):
    """
    TUI Window Manager CLI.
    Manages open application windows, layout modes (floating, docked, fullscreen),
    tiling, minimization, and window focus.
    """
    if flags.get("help"):
        return {"success": True, "output": help(args, flags, user_context)}

    if not args or args[0] in ("list", "ls"):
        return {
            "effect": "window_action",
            "action": "list"
        }

    subcmd = args[0].lower()

    if subcmd == "focus":
        if len(args) < 2:
            return {
                "success": False,
                "error": {
                    "message": "wm focus: missing window ID",
                    "suggestion": "Usage: wm focus <window_id>"
                }
            }
        return {
            "effect": "window_action",
            "action": "focus",
            "window_id": args[1]
        }

    if subcmd == "mode":
        if len(args) < 3:
            return {
                "success": False,
                "error": {
                    "message": "wm mode: missing window ID or mode",
                    "suggestion": "Usage: wm mode <window_id> <floating|docked-right|docked-left|docked-bottom|fullscreen>"
                }
            }
        mode = args[2].lower()
        valid = ("floating", "docked-right", "docked-left", "docked-bottom", "fullscreen")
        if mode not in valid:
            return {
                "success": False,
                "error": {
                    "message": f"wm mode: invalid layout mode '{mode}'",
                    "suggestion": f"Choose from: {', '.join(valid)}"
                }
            }
        return {
            "effect": "window_action",
            "action": "set_mode",
            "window_id": args[1],
            "mode": mode
        }

    if subcmd == "dock":
        if len(args) < 2:
            return {
                "success": False,
                "error": {
                    "message": "wm dock: missing window ID",
                    "suggestion": "Usage: wm dock <window_id> [right|left|bottom]"
                }
            }
        direction = args[2].lower() if len(args) > 2 else "right"
        if direction not in ("right", "left", "bottom"):
            return {
                "success": False,
                "error": {
                    "message": f"wm dock: invalid dock direction '{direction}'",
                    "suggestion": "Choose from: right, left, bottom"
                }
            }
        return {
            "effect": "window_action",
            "action": "dock",
            "window_id": args[1],
            "direction": direction
        }

    if subcmd == "float":
        if len(args) < 2:
            return {
                "success": False,
                "error": {
                    "message": "wm float: missing window ID",
                    "suggestion": "Usage: wm float <window_id>"
                }
            }
        return {
            "effect": "window_action",
            "action": "float",
            "window_id": args[1]
        }

    if subcmd in ("min", "minimize"):
        if len(args) < 2:
            return {
                "success": False,
                "error": {
                    "message": "wm min: missing window ID",
                    "suggestion": "Usage: wm min <window_id>"
                }
            }
        return {
            "effect": "window_action",
            "action": "minimize",
            "window_id": args[1]
        }

    if subcmd in ("restore", "unminimize"):
        if len(args) < 2:
            return {
                "success": False,
                "error": {
                    "message": "wm restore: missing window ID",
                    "suggestion": "Usage: wm restore <window_id>"
                }
            }
        return {
            "effect": "window_action",
            "action": "restore",
            "window_id": args[1]
        }

    if subcmd in ("close", "kill"):
        if len(args) < 2:
            return {
                "success": False,
                "error": {
                    "message": "wm close: missing window ID",
                    "suggestion": "Usage: wm close <window_id>"
                }
            }
        return {
            "effect": "window_action",
            "action": "close",
            "window_id": args[1]
        }

    if subcmd == "tile":
        return {
            "effect": "window_action",
            "action": "tile"
        }

    return {
        "success": False,
        "error": {
            "message": f"wm: unknown subcommand '{subcmd}'",
            "suggestion": "Run 'wm help' or 'man wm' to see available subcommands."
        }
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    wm - TUI Window Manager for FractalOS

SYNOPSIS
    wm [list]
    wm focus <window_id>
    wm mode <window_id> <mode>
    wm dock <window_id> [right|left|bottom]
    wm float <window_id>
    wm min <window_id>
    wm restore <window_id>
    wm close <window_id>
    wm tile

DESCRIPTION
    Manages interactive TUI windows for overlay and desktop applications
    (Editor, Paint, Top, Adventure, Netgame, Peers, Chidi, etc.).

    Allows running applications alongside the shell terminal in tiled,
    docked, or floating window viewports with independent focus and sizing.

SUBCOMMANDS
    list, ls
        List all open application windows, their layout modes and states.
    focus <id>
        Bring specified window to foreground and give it keyboard focus.
    mode <id> <floating|docked-right|docked-left|docked-bottom|fullscreen>
        Change the layout mode of the specified window.
    dock <id> [right|left|bottom]
        Tile window side-by-side with the shell terminal (default: right).
    float <id>
        Switch window to movable, resizable floating mode.
    min, minimize <id>
        Minimize window to the taskbar dock strip.
    restore <id>
        Restore minimized window to the active viewport.
    close <id>
        Close and exit the specified application window.
    tile
        Automatically arrange open windows in a tiled grid.

KEYBOARD SHORTCUTS
    Alt+D       Cycle dock modes (Dock Right -> Left -> Bottom -> Float)
    Alt+F       Toggle Fullscreen / Floating mode
    Alt+M       Minimize active window to taskbar dock
    Alt+Tab     Cycle focus between open windows and the shell terminal
    Esc         Exit active window application
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: wm [list|focus <id>|mode <id> <mode>|dock <id>|float <id>|min <id>|restore <id>|close <id>|tile]"
