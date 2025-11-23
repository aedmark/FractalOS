# gemini/core/commands/theme.py
import json
import os
from filesystem import fs_manager

THEME_DIR = "/etc/themes"

def define_flags():
    """Declares the flags that the theme command accepts."""
    return {'flags': [], 'metadata': {}}

def _ensure_theme_dir_exists(user_context):
    """Creates the /etc/themes directory if it doesn't exist."""
    if not fs_manager.get_node(THEME_DIR):
        try:
            if not fs_manager.get_node("/etc"):
                fs_manager.create_directory("/etc", {"name": "root", "group": "root"})
            fs_manager.create_directory(THEME_DIR, {"name": "root", "group": "root"})
            fs_manager.chmod(THEME_DIR, "755") # rwxr-xr-x
            return True
        except Exception:
            return False
    return True

def _find_theme_by_name(theme_name_to_find):
    """Finds a theme file by its 'name' property and returns its content."""
    theme_node = fs_manager.get_node(THEME_DIR)
    if not theme_node or theme_node.get('type') != 'directory':
        return None

    for name, node in theme_node.get('children', {}).items():
        if name.endswith('.json'):
            try:
                theme_data = json.loads(node.get('content', '{}'))
                if theme_data.get('name', '').lower() == theme_name_to_find.lower():
                    return node.get('content')
            except json.JSONDecodeError:
                continue
    return None

def run(args, flags, user_context, **kwargs):
    """Manages system-wide visual and auditory themes."""
    if not _ensure_theme_dir_exists(user_context):
        return {"success": False, "error": {"message": "theme: could not create themes directory", "suggestion": "Check permissions for /etc."}}

    if not args or args[0].lower() == 'list':
        theme_node = fs_manager.get_node(THEME_DIR)
        theme_files = []
        if theme_node and theme_node.get('type') == 'directory':
            for name, node in theme_node.get('children', {}).items():
                if name.endswith('.json') and node.get('type') == 'file':
                    try:
                        theme_data = json.loads(node.get('content', '{}'))
                        theme_name = theme_data.get('name', os.path.splitext(name)[0])
                        theme_files.append(f"- {theme_name}")
                    except json.JSONDecodeError:
                        continue
        if not theme_files:
            return "No themes found in /etc/themes."
        return "Available themes:\n" + "\n".join(sorted(theme_files))

    sub_command = args[0].lower()

    if sub_command == 'apply':
        if len(args) < 2:
            return {"success": False, "error": {"message": "theme: missing theme name", "suggestion": "Usage: theme apply <theme_name>"}}

        theme_to_apply = " ".join(args[1:])
        theme_content = _find_theme_by_name(theme_to_apply)

        if theme_content:
            theme_data = json.loads(theme_content)
            return {"effect": "apply_theme", "themeName": theme_data.get('name')}

        return {"success": False, "error": {"message": f"theme: theme '{theme_to_apply}' not found", "suggestion": "Use 'theme list' to see available themes."}}

    if sub_command == 'get':
        if len(args) < 2:
            return {"success": False, "error": {"message": "theme: missing theme name for get", "suggestion": "Usage: theme get <theme_name>"}}

        theme_to_get = " ".join(args[1:])
        theme_content = _find_theme_by_name(theme_to_get)

        if theme_content:
            return theme_content # Return the raw JSON string

        return {"success": False, "error": {"message": f"theme: theme '{theme_to_get}' not found"}}

    return {"success": False, "error": {"message": f"theme: unknown sub-command '{sub_command}'", "suggestion": "Available commands are: list, apply, get."}}


def man(args, flags, user_context, **kwargs):
    return """
NAME
    theme - Manages the visual and auditory theme of the OS.

SYNOPSIS
    theme [list|apply <theme_name>|get <theme_name>]

DESCRIPTION
    Allows users to list, apply, or retrieve data for themes. Themes are stored as .json files in /etc/themes/.

SUB-COMMANDS
    list
        (Default) Lists all available themes.
    apply <theme_name>
        Applies the specified theme to the system.
    get <theme_name>
        Outputs the raw JSON data for the specified theme. (Internal use)
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: theme [list|apply <theme_name>]"