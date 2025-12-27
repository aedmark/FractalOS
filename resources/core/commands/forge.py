# gem/core/commands/forge.py

from filesystem import fs_manager

def run(args, flags, user_context, **kwargs):
    """
    Writes content to a file.
    Usage: forge <filename> <content>
    """
    if len(args) < 2:
        return {
            "success": False,
            "error": {
                "message": "forge: missing arguments",
                "suggestion": "Usage: forge <filename> \"<content>\""
            }
        }

    target_file = args[0]
    # Join all remaining args as content (in case quotes were weird), but usually args[1] is the string.
    # We also replace literal '\n' with actual newlines to allow one-line writing of multi-line scripts.
    content = " ".join(args[1:]).replace("\\n", "\n")

    try:
        # We assume the user wants to OVERWRITE. To append, they should use 'append' flag (future).
        fs_manager.write_file(target_file, content, user_context)
        return f"Forged '{target_file}' ({len(content)} bytes)."
    except Exception as e:
        return {
            "success": False,
            "error": {
                "message": f"forge: failed to write '{target_file}': {str(e)}",
                "suggestion": "Check permissions and path."
            }
        }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    forge - write content to a file

SYNOPSIS
    forge <filename> "<content>"

DESCRIPTION
    Writes the provided string content to the specified file.
    It automatically converts literal '\\n' characters into actual newlines,
    allowing you to write multi-line scripts in a single command.

EXAMPLES
    forge hello.py "print('Hello World')\\nprint('Done')"
"""

def help(args, flags, user_context, **kwargs):
    return 'Usage: forge <filename> "<content>"'
