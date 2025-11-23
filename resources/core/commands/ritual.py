# gemini/core/commands/ritual.py

import shlex

def define_flags():
    """Declares the flags that the ritual command accepts."""
    return { 'flags': [], 'metadata': {} }

def run(args, flags, user_context, **kwargs):
    """Performs a multi-step, atmospheric ritual by executing a sequence of commands."""
    if not args:
        return {
            "success": False,
            "error": {
                "message": "ritual: you must specify which ritual to perform.",
                "suggestion": "Available rituals are: cleansing, focus, awakening."
            }
        }

    ritual_name = args[0].lower()
    commands_to_run = []

    if ritual_name == "cleansing":
        commands_to_run = [
            "delay 400",
            "printf 'The sage is lit...'",
            "delay 1600",
            "clear",
            "printf 'Release all bad energies from the mind and body.'",
            "delay 5000",
            "play E6 20n; play F6 32n; play F#6 32n; play A6 32n; play D7 64n",
            "clear",
            "delay 2000",
            "printf 'This house... is clean.'",
            "delay 500"
        ]
    elif ritual_name == "focus":
        commands_to_run = [
            "delay 400",
            "printf 'Clear your mind.'",
            "delay 1600",
            "clear",
            "delay 2500",
            "play C3 8n",
            "printf 'Filter your thoughts...'",
            "delay 3500",
            "play C4 8n",
            "printf '\nFocus your intent.'",
            "delay 5000",
            "printf '\nBegin.'",
            "play C5 6n",
            "delay 400"
        ]
    elif ritual_name == "awakening":
        commands_to_run = [
            "printf 'The machine spirit has been summoned...'",
            "delay 1200",
            "clear",
            "printf 'The machine spirit stirs from its slumber...\n \n'",
            "delay 2500",
            "echo 'System Time:'",
            "date",
            "echo '\n \nCurrent User:'",
            "whoami",
            "echo '\n \nSession Duration:'",
            "uptime",
            "echo '\n \nActive Daemons:'",
            "ps"
        ]
    else:
        return {
            "success": False,
            "error": {
                "message": f"ritual: unknown ritual '{ritual_name}'.",
                "suggestion": "Available rituals are: cleansing, focus, awakening."
            }
        }

    return {
        "effect": "execute_commands",
        "commands": commands_to_run
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    ritual - Perform a multi-step, atmospheric ritual.

SYNOPSIS
    ritual <name>

DESCRIPTION
    A ritual is a performative act that prepares the system and the magician for magical workings. It is not one action, but a sequence of commands, sounds, and delays designed to create a sympathetic environment for the intended spellcraft. It turns mere execution into a deliberate act of will.

AVAILABLE RITUALS
    cleansing
        Clears the terminal screen and confirms the space is prepared for new work.

    focus
        Aids the magician in centering their thoughts before a complex task. It clears the screen, plays a low tone, and displays a series of focusing prompts.

    awakening
        Performs a system-wide check to greet the 'machine spirit'. It reports the current time, user, uptime, and active processes in a thematic way.

EXAMPLES
    ritual cleansing
    ritual focus
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: ritual <cleansing|focus|awakening>"