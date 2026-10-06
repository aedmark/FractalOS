"""
focus.py - Switch focus between terminal split panes.
"""
from commands import split

def define_flags():
    return split.define_flags()

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    return await split.run(["focus", *args], flags, user_context, stdin_data, **kwargs)

def man(args, flags, user_context, **kwargs):
    return """
NAME
    focus - switch focus between terminal split panes

SYNOPSIS
    focus <paneId|index|next|prev>

DESCRIPTION
    Switches active input focus and working directory context to the specified
    terminal pane. Supports pane index (e.g. 'focus 2'), pane ID (e.g. 'focus pane-2'),
    or relative navigation ('focus next', 'focus prev').

SEE ALSO
    split, panes, close-pane
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: focus <paneId|index|next|prev>"
