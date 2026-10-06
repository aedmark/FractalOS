"""
split.py - Terminal Split Panes & Multiplexing for FractalOS (P7-09).
Provides horizontal and vertical pane splits, pane focus navigation,
zoom toggling, and pane lifecycle management.
"""

def define_flags():
    return {
        "flags": [
            "--vertical", "-v",
            "--horizontal", "-h",
            "--command", "-c",
            "--list", "-l",
            "--close", "-x",
            "--zoom", "-z",
            "--focus", "-f",
            "--help",
            "-help"
        ],
        "metadata": {
            "--command": {"type": "string"},
            "-c": {"type": "string"},
            "--focus": {"type": "string"},
            "-f": {"type": "string"}
        }
    }

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    subcmd = str(args[0]).strip().lower() if args else ""

    # Check subcommands or flags
    if subcmd in {"list", "ls"} or "--list" in flags or "-l" in flags:
        return {
            "effect": "multiplexer_action",
            "action": "list"
        }

    if subcmd in {"close", "kill", "rm"} or "--close" in flags or "-x" in flags:
        target_id = args[1] if len(args) > 1 else None
        return {
            "effect": "multiplexer_action",
            "action": "close",
            "paneId": target_id
        }

    if subcmd in {"focus", "switch"} or "--focus" in flags or "-f" in flags:
        target_id = None
        if len(args) > 1:
            target_id = args[1]
        elif "--focus" in flags:
            target_id = flags["--focus"]
        elif "-f" in flags:
            target_id = flags["-f"]
        return {
            "effect": "multiplexer_action",
            "action": "focus",
            "paneId": target_id
        }

    if subcmd in {"zoom", "z", "max"} or "--zoom" in flags or "-z" in flags:
        target_id = args[1] if len(args) > 1 else None
        return {
            "effect": "multiplexer_action",
            "action": "zoom",
            "paneId": target_id
        }

    # Determine orientation: vertical (default or -v / v) or horizontal (-h / h)
    orientation = "vertical"
    if subcmd in {"h", "horizontal"} or "--horizontal" in flags or "-h" in flags:
        orientation = "horizontal"
    elif subcmd in {"v", "vertical"} or "--vertical" in flags or "-v" in flags:
        orientation = "vertical"

    # Command to run in new pane
    cmd_to_run = None
    if "--command" in flags:
        cmd_to_run = flags["--command"]
    elif "-c" in flags:
        cmd_to_run = flags["-c"]
    elif len(args) > 1 and subcmd in {"v", "h", "vertical", "horizontal"}:
        cmd_to_run = " ".join(args[1:])

    return {
        "effect": "multiplexer_action",
        "action": f"split_{orientation}",
        "orientation": orientation,
        "command": cmd_to_run
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    split - split terminal into multiple panes and manage multiplexer layout

SYNOPSIS
    split [-v|-h] [-c <command>]
    split list
    split focus <paneId|next|prev>
    split close [paneId]
    split zoom [paneId]

DESCRIPTION
    The split command multiplexes the FractalOS terminal interface into multiple
    horizontal or vertical split panes with independent working directories,
    command histories, and output buffers.

OPTIONS
    --vertical, -v
        Splits the current pane vertically (side-by-side, default).
    --horizontal, -h
        Splits the current pane horizontally (top and bottom).
    --command, -c <cmd>
        Automatically executes <cmd> inside the newly created pane upon creation.
    --list, -l
        Lists all currently active panes, their working directories, and active status.
    --focus, -f <id>
        Switches focus to the specified pane ID or index (or 'next'/'prev').
    --close, -x [id]
        Closes the specified pane (or the currently focused pane).
    --zoom, -z
        Toggles maximizing the active pane to fullscreen and unzooming.

KEYBOARD SHORTCUTS
    Alt+V        Split active pane vertically
    Alt+H        Split active pane horizontally
    Alt+W        Close active pane
    Alt+Z        Toggle zoom active pane to fullscreen
    Alt+Right    Focus next pane
    Alt+Left     Focus previous pane

EXAMPLES
    split -v
        Splits the terminal into left and right panes.

    split -h -c "top"
        Splits horizontally and opens the 'top' process monitor in the lower pane.

    split list
        Displays all open panes and their directories.

    split focus 2
        Focuses pane 2.

SEE ALSO
    split-v, split-h, panes, focus, close-pane
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: split [-v|-h] [-c <cmd>] | split list | split focus <id> | split close [id]"
