# gemini/resources/core/commands/story.py

import os
import json
import shlex
from datetime import datetime
from filesystem import fs_manager
from story_manager import story_manager

def define_flags():
    """Declares the flags that the story command accepts."""
    return {
        'flags': [
            {'name': 'confirmed', 'long': 'confirmed', 'takes_value': True, "hidden": True},
        ],
        'metadata': {}
    }

def run(args, flags, user_context, **kwargs):
    """Manages the story version control system."""
    if not args:
        return {
            "success": False,
            "error": {
                "message": "story: missing sub-command",
                "suggestion": "Try 'story begin', 'story save', 'story log', or 'story rewind'. See 'man story' for details."
            }
        }

    sub_command = args[0].lower()
    current_path = fs_manager.current_path
    story_path = story_manager._get_story_path(current_path)

    if sub_command != "begin" and not story_path:
        return {"success": False, "error": {"message": "story: not a story repository.", "suggestion": "Run 'story begin' to start a new story here."}}

    if sub_command == "begin":
        result = story_manager.init(current_path, user_context)
        if result["success"]:
            return "This story has begun."
        else:
            return {"success": False, "error": {"message": result["error"], "suggestion": "You may have already started a story in this directory or one of its parents."}}

    elif sub_command == "save":
        if len(args) < 2:
            return {"success": False, "error": {"message": "story: missing commit message", "suggestion": "Usage: story save \"<message>\""}}

        message = " ".join(args[1:])
        snapshot_result = story_manager.create_snapshot(os.path.dirname(story_path), user_context)

        if not snapshot_result["success"]:
            return {"success": False, "error": {"message": snapshot_result["error"]}}

        snapshot_id = snapshot_result["snapshot_id"]
        log_result = story_manager.add_log_entry(story_path, message, snapshot_id, user_context)

        if not log_result["success"]:
            return {"success": False, "error": {"message": log_result["error"]}}

        return f"Chapter saved: {snapshot_id} - {message}"

    elif sub_command == "log":
        log_result = story_manager.read_log(story_path)
        if not log_result["success"]:
            return {"success": False, "error": {"message": log_result["error"]}}

        log_data = log_result["data"]
        if not log_data:
            return "No chapters have been saved yet."

        output = []
        for entry in log_data:
            dt_obj = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
            date_str = dt_obj.strftime('%Y-%m-%d %H:%M:%S %Z')
            output.append(f"chapter {entry['id']}")
            output.append(f"Author: {entry.get('author', 'unknown')}")
            output.append(f"Date:   {date_str}")
            output.append(f"\n    {entry['message']}\n")

        return "\\n".join(output)

    elif sub_command == "rewind":
        if len(args) < 2:
            return {"success": False, "error": {"message": "story: missing chapter ID to rewind to", "suggestion": "Usage: story rewind <id>"}}

        snapshot_id = args[1]
        confirmed_id = flags.get("confirmed")

        # Check if this run is the result of a confirmation
        if confirmed_id == snapshot_id:
            restore_result = story_manager.restore_snapshot(os.path.dirname(story_path), snapshot_id, user_context)
            if restore_result["success"]:
                return f"Rewound to chapter {snapshot_id}."
            else:
                return {"success": False, "error": {"message": restore_result["error"]}}

        # If not confirmed, send the confirmation effect
        return {
            "effect": "confirm",
            "message": [
                "WARNING: This will overwrite your current files with the state from the selected chapter.",
                "This action cannot be undone. Are you sure you want to rewind?",
            ],
            "on_confirm_command": f"story rewind {shlex.quote(snapshot_id)} --confirmed={shlex.quote(snapshot_id)}"
        }

    else:
        return {"success": False, "error": {"message": f"story: unknown sub-command '{sub_command}'"}}

def man(args, flags, user_context, **kwargs):
    return """
NAME
story - A narrative-driven version control system.

SYNOPSIS
story <sub-command> [options]

DESCRIPTION
Manages the history of a project as a series of named "chapters" (snapshots). It's designed to be simple, safe, and intuitive.

SUB-COMMANDS:
begin
Initializes a new story in the current directory, creating a hidden .story folder to track history.
save "<message>"
Saves the current state of all non-hidden files as a new chapter with the given message.
log
Displays the history of all saved chapters, from newest to oldest.
rewind <id>
Restores the project's files to the state of the specified chapter ID. This is a destructive action and will require confirmation.

EXAMPLES:
story begin
story save "Initial draft of the introduction."
story log
story rewind a1b2c3d4e5
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: story <begin|save|log|rewind> [options]"