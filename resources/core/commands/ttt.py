"""
ttt.py - Shortcut for Tic-Tac-Toe terminal game.
"""

from commands import netgame

def run(args, flags, user_context, **kwargs):
    if not args:
        if "--bot" in flags or "-b" in flags:
            return netgame.run(["bot", "ttt"], flags, user_context, **kwargs)
        if "--gui" in flags or "-g" in flags:
            return netgame.run(["play", "ttt"], flags, user_context, **kwargs)
        session = netgame._get_active_session(user_context.get("username", "guest"))
        if session and session.get("gameType") == "ttt":
            return netgame.run(["status"], flags, user_context, **kwargs)
        return netgame.run(["host", "ttt"], flags, user_context, **kwargs)

    first = args[0].lower()
    if first.isdigit():
        return netgame.run(["move", first], flags, user_context, **kwargs)
    elif first in ("move", "m"):
        return netgame.run(["move"] + args[1:], flags, user_context, **kwargs)
    elif first in ("bot", "ai"):
        return netgame.run(["bot", "ttt"], flags, user_context, **kwargs)
    elif first in ("board", "status", "resign", "close", "accept"):
        return netgame.run(args, flags, user_context, **kwargs)
    elif first in ("play", "gui"):
        return netgame.run(["play", "ttt"] + args[1:], flags, user_context, **kwargs)
    else:
        return netgame.run(["host", "ttt", args[0]], flags, user_context, **kwargs)

def man(args, flags, user_context, **kwargs):
    return """
NAME
    ttt - Tic-Tac-Toe terminal game

SYNOPSIS
    ttt [peer] [--bot] [--gui]
    ttt <1-9>
    ttt move <1-9>
    ttt board
    ttt bot
    ttt resign

DESCRIPTION
    Direct shortcut for Tic-Tac-Toe in FractalOS.
    See 'man netgame' for full details.
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: ttt [peer | <1-9> | bot | board | resign]"
