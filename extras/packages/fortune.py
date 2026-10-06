"""
fortune - Display random fortunes and pearls of FractalOS wisdom
"""
import random

FORTUNES = [
    "The fractal does not fear the zoom; at every scale, it remains itself.",
    "Computers are like Old Testament gods: lots of rules and no mercy. -- Joseph Campbell",
    "To understand recursion, one must first understand recursion.",
    "There are only 10 types of people in the world: those who understand binary, and those who don't.",
    "Inside every large program is a small program struggling to get out.",
    "Simplicity is prerequisite for reliability. -- Edsger W. Dijkstra",
    "A journey of a thousand nodes begins with a single handshake.",
    "The best way to predict the future is to invent it. -- Alan Kay",
    "Do not fear the glitch; the glitch is the computer's subconscious speaking.",
    "Hardware eventually fails. Software eventually works.",
    "In the shell, silence is golden. When in doubt, return exit code 0.",
    "You will find happiness in unexpected branches of the file tree.",
    "A clean status bar is the sign of a peaceful process scheduler.",
    "Remember: In Pyodide WebAssembly, nobody can hear you segfault.",
    "The cow knows all, but speaks only in ASCII."
]

def metadata():
    return {
        "name": "fortune",
        "version": "1.0.0",
        "description": "Prints random humorous and philosophical fortunes",
        "author": "FractalOS Community",
        "license": "MIT",
        "wheels": [],
        "dependencies": []
    }

def define_flags():
    return {
        "flags": [
            {"name": "help", "short": "h", "long": "help", "takes_value": False},
            {"name": "short", "short": "s", "long": "short", "takes_value": False},
            {"name": "color", "short": "C", "long": "color", "takes_value": False},
        ],
        "aliases": {"h": "help", "s": "short", "C": "color"}
    }

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    if flags.get("help"):
        return {"success": True, "output": help(args, flags, user_context)}

    pool = FORTUNES
    if flags.get("short"):
        pool = [f for f in FORTUNES if len(f) <= 60]

    chosen = random.choice(pool) if pool else random.choice(FORTUNES)
    if flags.get("color"):
        return f"\x1b[1;36m{chosen}\x1b[0m"
    return chosen

def man(args, flags, user_context, **kwargs):
    return """
NAME
    fortune - Print a random, hopefully interesting, adage

SYNOPSIS
    fortune [-s|--short]

DESCRIPTION
    Selects and displays a random adage, quote, or pearl of wisdom from
    the FractalOS community fortune database.

OPTIONS
    -s, --short
        Select only shorter fortunes (60 characters or less).

EXAMPLES
    fortune
    fortune | cowsay
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: fortune [-s|--short]"
