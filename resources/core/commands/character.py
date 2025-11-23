# gemini/core/commands/character.py

import os
from filesystem import fs_manager

def define_flags():
    """Declares the flags that the character command accepts."""
    return {'flags': [], 'metadata': {}}

def run(args, flags, user_context, **kwargs):
    """
    Manages TTRPG characters by intelligently using binder, log, and planner.
    """
    if not args:
        return {
            "success": False,
            "error": {
                "message": "character: missing sub-command",
                "suggestion": "Try 'character create <name>', 'character journal <name>', or 'character quests <name>'."
            }
        }

    sub_command = args[0].lower()

    if sub_command == "create":
        if len(args) != 2:
            return {"success": False, "error": {"message": "character: missing character name", "suggestion": "Usage: character create <name>"}}

        char_name = args[1]
        binder_name = f"{char_name}.binder"
        journal_path = f"/home/{user_context.get('name')}/.journal"
        planner_path = f"/home/{user_context.get('name')}/.plans/{char_name}_quests.planner"
        sheet_path = f"/home/{user_context.get('name')}/{char_name}_sheet.md"

        commands_to_run = [
            f'binder create "{binder_name}"',
            f'touch "{sheet_path}"',
            f'planner create "{char_name}_quests"',
            f'binder add "{binder_name}" "{sheet_path}" -s sheet',
            f'binder add "{binder_name}" "{planner_path}" -s quests'
        ]

        return {
            "effect": "execute_commands",
            "commands": commands_to_run,
            "output": f"Character '{char_name}' created! Binder, character sheet, and quest log are ready."
        }

    # All other commands require a character name
    if len(args) < 2:
        return {"success": False, "error": {"message": f"character: missing character name for '{sub_command}'", "suggestion": f"Usage: character {sub_command} <name>"}}

    char_name = args[1]
    binder_name = f"{char_name}.binder"

    # Check if the binder exists as a proxy for the character
    if not fs_manager.get_node(binder_name):
        return {"success": False, "error": {"message": f"character: no character named '{char_name}' found", "suggestion": "Create the character first with 'character create <name>'."}}


    if sub_command == "journal":
        message = " ".join(args[2:])
        if not message:
            return {"success": False, "error": {"message": "character: missing journal entry text", "suggestion": f'Usage: character journal {char_name} "Your entry here"'}}

        # We'll tag the log entry to make it searchable
        tagged_message = f"# {char_name}\\n\\n{message}"

        return {
            "effect": "execute_commands",
            "commands": [f'log -n "{tagged_message}"'],
            "output": f"Journal entry added for {char_name}."
        }

    elif sub_command == "quests":
        planner_name = f"{char_name}_quests"
        planner_args = " ".join(args[2:])
        if not planner_args:
            return {"success": False, "error": {"message": "character: missing quest command", "suggestion": f"Usage: character quests {char_name} <add|done|list> [options]"}}

        return {
            "effect": "execute_commands",
            "commands": [f'planner "{planner_name}" {planner_args}'],
        }

    elif sub_command == "open":
        return {
            "effect": "execute_commands",
            "commands": [f'edit "{char_name}_sheet.md"'],
        }

    else:
        return {"success": False, "error": {"message": f"character: unknown sub-command '{sub_command}'"}}


def man(args, flags, user_context, **kwargs):
    return """
NAME
    character - A tool suite for managing tabletop RPG characters.

SYNOPSIS
    character <sub-command> <character_name> [options]

DESCRIPTION
    Manages all aspects of a TTRPG character by creating a centralized binder and providing easy access to journals, quest logs, and character sheets.

SUB-COMMANDS:
    create <name>
        Creates a new character suite: a binder, a character sheet, and a quest planner.
    
    open <name>
        Opens the character sheet for the specified character in the editor.

    journal <name> "<entry>"
        Adds a new timestamped journal entry to the system log, tagged with the character's name.
        
    quests <name> [planner_command]
        Manages the character's quest log using the 'planner' tool. (e.g., 'quests <name> add "Slay the dragon"')

EXAMPLES:
    character create GrogStrongjaw
    character open GrogStrongjaw
    character journal GrogStrongjaw "I would like to rage."
    character quests GrogStrongjaw list
    character quests GrogStrongjaw add "Find more ale."
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: character <create|open|journal|quests> <name> [options]"