# gem/core/commands/forge.py

import re

from filesystem import fs_manager

def define_flags():
    return [{'name': 'literal', 'long': 'literal', 'takes_value': False}]


def decode_content(content):
    """Decode one forge layer: backslash-n is newline, doubled backslash is literal.

    Other escapes remain unchanged; this is deliberately not unicode_escape.
    Shell quoting is a separate earlier layer (single quotes preserve backslashes).
    """
    return re.sub(r"\\(\\|n)", lambda match: "\n" if match[1] == "n" else "\\", content)


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
    content = " ".join(args[1:])
    if not flags.get('literal'):
        content = decode_content(content)

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
    return r"""
NAME
    forge - write content to a file

SYNOPSIS
    forge [--literal] <filename> "<content>"

DESCRIPTION
    Writes the supplied text. After shell quoting, \n becomes a newline and
    \\ becomes a literal backslash. Other escapes are preserved.
    --literal disables this decoding and writes the argument exactly as received.
    Single-quote shell content to preserve its backslashes. With double-quoted
    shell content, double backslashes again for the shell layer.

EXAMPLES
    forge hello.py 'print("Hello World")\nprint("Done")'
    forge nested.py 'print("first\\nsecond")'
    forge --literal note.txt 'Keep this \n literally'
"""


def help(args, flags, user_context, **kwargs):
    return 'Usage: forge [--literal] <filename> "<content>"'
