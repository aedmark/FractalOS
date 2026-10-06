"""
c4.py - Shortcut for Connect 4 multiplayer terminal game.
"""

from commands import netgame

def run(args, flags, user_context, **kwargs):
    if not args:
        # Default: if run with no args, host or play c4
        if "--bot" in flags or "-b" in flags:
            return netgame.run(["bot", "c4"], flags, user_context, **kwargs)
        if "--gui" in flags or "-g" in flags:
            return netgame.run(["play", "c4"], flags, user_context, **kwargs)
        # Check active session
        session = netgame._get_active_session(user_context.get("username", "guest"))
        if session and session.get("gameType") == "c4":
            return netgame.run(["status"], flags, user_context, **kwargs)
        return netgame.run(["host", "c4"], flags, user_context, **kwargs)

    first = args[0].lower()
    if first.isdigit():
        return netgame.run(["move", first], flags, user_context, **kwargs)
    elif first in ("move", "m"):
        return netgame.run(["move"] + args[1:], flags, user_context, **kwargs)
    elif first in ("bot", "ai"):
        return netgame.run(["bot", "c4"], flags, user_context, **kwargs)
    elif first in ("board", "status", "resign", "close", "accept"):
        return netgame.run(args, flags, user_context, **kwargs)
    elif first in ("play", "gui"):
        return netgame.run(["play", "c4"] + args[1:], flags, user_context, **kwargs)
    else:
        # Peer name? e.g. 'c4 bob' -> host c4 bob
        return netgame.run(["host", "c4", args[0]], flags, user_context, **kwargs)

def man(args, flags, user_context, **kwargs):
    return """
NAME
    c4 - Connect 4 terminal multiplayer game

SYNOPSIS
    c4 [peer] [--bot] [--gui]
    c4 <1-7>
    c4 move <1-7>
    c4 board
    c4 bot
    c4 resign

DESCRIPTION
    Direct shortcut for Connect 4 in FractalOS.
    See 'man netgame' for full details.
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: c4 [peer | <1-7> | bot | board | resign]"
