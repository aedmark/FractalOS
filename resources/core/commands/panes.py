"""
panes.py - List all active terminal split panes.
"""
from commands import split

def define_flags():
    return split.define_flags()

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    return await split.run(["list", *args], flags, user_context, stdin_data, **kwargs)

def man(args, flags, user_context, **kwargs):
    return """
NAME
    panes - list all active terminal split panes

SYNOPSIS
    panes

DESCRIPTION
    Displays a list of all active terminal multiplexer panes, their identifiers,
    current working directories, and whether they are active or zoomed.

SEE ALSO
    split, focus, close-pane
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: panes"
