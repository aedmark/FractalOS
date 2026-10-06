"""
split_h.py - Split terminal pane horizontally (top and bottom).
"""
from commands import split

def define_flags():
    return split.define_flags()

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    flags["--horizontal"] = True
    return await split.run(["horizontal", *args], flags, user_context, stdin_data, **kwargs)

def man(args, flags, user_context, **kwargs):
    return """
NAME
    split-h - split the active terminal pane horizontally (top and bottom)

SYNOPSIS
    split-h [-c <command>]

DESCRIPTION
    Splits the active terminal pane into two horizontal (top and bottom) panes.
    Shortcut for 'split -h'.

SEE ALSO
    split, split-v, panes, close-pane
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: split-h [-c <command>]"
