# gemini/core/commands/cast.py

import os
from filesystem import fs_manager
from datetime import datetime, timedelta
import re
import shlex

def define_flags():
    """Declares the flags that this command accepts."""
    return {
        'flags': [],
        'metadata': {}
    }

def _parse_duration(duration_str):
    """Parses a duration string like '5m', '1h', '30s' into a timedelta."""
    match = re.match(r'(\d+)([smh])', duration_str)
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    if unit == 's':
        return timedelta(seconds=value)
    if unit == 'm':
        return timedelta(minutes=value)
    if unit == 'h':
        return timedelta(hours=value)
    return None

def run(args, flags, user_context, **kwargs):
    """Casts a spell."""
    if not args:
        return {
            "success": False,
            "error": {
                "message": "cast: missing spell name",
                "suggestion": "Try 'cast ward <file> [duration]'."
            }
        }

    spell_name = args[0].lower()

    if spell_name == "ward":
        if len(args) < 2:
            return {
                "success": False,
                "error": {
                    "message": "cast ward: missing target",
                    "suggestion": "Usage: cast ward <file_or_directory> [duration]"
                }
            }
        target_path = args[1]
        duration_str = args[2] if len(args) > 2 else "5m" # Default to 5 minutes

        target_node = fs_manager.get_node(target_path)
        if not target_node:
            return {
                "success": False,
                "error": {
                    "message": f"cast ward: target '{target_path}' not found",
                    "suggestion": "Please specify an existing file or directory."
                }
            }

        duration = _parse_duration(duration_str)
        if not duration:
            return {
                "success": False,
                "error": {
                    "message": f"cast ward: invalid duration format '{duration_str}'",
                    "suggestion": "Use 's' for seconds, 'm' for minutes, 'h' for hours (e.g., '30s', '10m', '1h')."
                }
            }

        original_mode = target_node.get('mode', 0o755)
        ward_mode = original_mode & 0o555  # Remove write permissions for everyone

        future_time = datetime.utcnow() + duration
        cron_string = f"{future_time.minute} {future_time.hour} {future_time.day} {future_time.month} *"

        # Corrected command string for the agenda. No excessive escaping.
        unward_command = f'chmod {oct(original_mode)[2:]} "{target_path}"'
        schedule_command = f'agenda add "{cron_string}" "{unward_command}"'
        ward_command = f'chmod {oct(ward_mode)[2:]} "{target_path}"'

        return {
            "effect": "execute_commands",
            "commands": [
                ward_command,
                schedule_command
            ],
            "output": f"Warding '{target_path}' for {duration_str}. It is now read-only."
        }

    else:
        return {
            "success": False,
            "error": {
                "message": f"cast: unknown spell '{spell_name}'",
                "suggestion": "Currently, only the 'ward' spell is known."
            }
        }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    cast - performs a magical spell within the OS

SYNOPSIS
    cast <spell> [options]

DESCRIPTION
    The cast command allows the user to perform magical spells that have tangible effects on the operating system's state.

SPELLS
    ward <file_or_directory> [duration]
        Temporarily makes a file or directory read-only for all users. The default duration is 5 minutes. The duration format is a number followed by 's' (seconds), 'm' (minutes), or 'h' (hours).

EXAMPLES
    cast ward secret.txt 10m
        Makes 'secret.txt' read-only for 10 minutes.
    cast ward /home/shared_project
        Wards the shared project directory for 5 minutes.
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: cast <spell> [options]"