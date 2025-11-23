# gemini/core/commands/cinematic.py

def define_flags():
    """Declares the flags that the cinematic command accepts."""
    return {'flags': [], 'metadata': {}}

def run(args, flags, user_context, **kwargs):
    """
    Toggles cinematic (typewriter) mode for the terminal.
    """
    if len(args) > 1:
        return {
            "success": False,
            "error": {
                "message": "cinematic: too many arguments",
                "suggestion": "Usage: cinematic [on|off]"
            }
        }

    mode = None
    if args:
        mode = args[0].lower()
        if mode not in ['on', 'off']:
            return {
                "success": False,
                "error": {
                    "message": f"cinematic: invalid mode '{args[0]}'",
                    "suggestion": "Please use 'on' or 'off'."
                }
            }

    return {
        "effect": "toggle_cinematic_mode",
        "mode": mode
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    cinematic - Toggles the cinematic typewriter effect for terminal output.

SYNOPSIS
    cinematic [on|off]

DESCRIPTION
    Engages or disengages a cinematic mode where all terminal output is
    displayed character by character, creating a dramatic, retro effect.
    Running the command without an argument toggles the current state.

OPTIONS
    This command takes no options.

EXAMPLES
    cinematic on
    cinematic off
    cinematic
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: cinematic [on|off]"