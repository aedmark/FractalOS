"""
split_v.py - Split terminal pane vertically (side-by-side).
"""
from commands import split

def define_flags():
    return split.define_flags()

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    flags["--vertical"] = True
    return await split.run(["vertical", *args], flags, user_context, stdin_data, **kwargs)

def man(args, flags, user_context, **kwargs):
    return """
NAME
    split-v - split the active terminal pane vertically (side-by-side)

SYNOPSIS
    split-v [-c <command>]

DESCRIPTION
    Splits the active terminal pane into two vertical (left and right) panes.
    Shortcut for 'split -v'.

SEE ALSO
    split, split-h, panes, close-pane
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: split-v [-c <command>]"
