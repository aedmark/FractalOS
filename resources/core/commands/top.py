def define_flags():
    return {
        "flags": ["dock", "float", "full"],
        "aliases": {"d": "dock", "f": "float"}
    }

def run(args, flags, user_context, **kwargs):
    """
    Returns an effect to launch the Top UI (process viewer).
    """
    if args:
        return {
            "success": False,
            "error": {
                "message": "top: command takes no arguments",
                "suggestion": "Run 'top' or 'top --dock' / 'top --float'."
            }
        }

    window_mode = "docked-right"
    if flags.get("float"):
        window_mode = "floating"
    elif flags.get("full"):
        window_mode = "fullscreen"
    elif flags.get("dock"):
        window_mode = "docked-right"

    return {
        "effect": "launch_app",
        "app_name": "Top",
        "options": {
            "windowMode": window_mode
        }
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    top - display a real-time view of running processes

SYNOPSIS
    top [--dock|-d] [--float|-f] [--full]

DESCRIPTION
    Provides a dynamic, real-time view of the processes running in FractalOS.
    The top command opens a process viewer window listing all active
    background jobs and system processes. By default it docks side-by-side
    with the terminal. Press 'q' or 'Escape' to quit.

OPTIONS
    -d, --dock
        Dock side-by-side with the shell terminal (default).
    -f, --float
        Open in a floating, movable window.
    --full
        Open in fullscreen overlay mode.

EXAMPLES
    top
    top --float
    top -d
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: top [--dock|-d] [--float|-f] [--full]"