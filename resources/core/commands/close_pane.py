"""
close_pane.py - Close a terminal split pane.
"""
from commands import split

def define_flags():
    return split.define_flags()

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    return await split.run(["close", *args], flags, user_context, stdin_data, **kwargs)

def man(args, flags, user_context, **kwargs):
    return """
NAME
    close-pane - close a terminal split pane

SYNOPSIS
    close-pane [paneId|index]

DESCRIPTION
    Closes the specified terminal split pane (or the currently focused pane if omitted).
    When only one pane remains, it cannot be closed.

SEE ALSO
    split, focus, panes
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: close-pane [paneId|index]"
