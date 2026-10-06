"""
cowsay - Configurable speaking ASCII cow and friends
"""
import textwrap

COWS = {
    "default": r"""
        \   ^__^
         \  ({eyes})\_______
            (__)\       )\/\
             {tongue} ||----w |
                ||     ||
""",
    "tux": r"""
   \
    \
        .--.
       |o_o |
       |:_/ |
      //   \ \
     (|     | )
    /'\_   _/`\
    \___)=(___/
""",
    "duck": r"""
 \
  \ >()_
     (__)__ _
""",
    "ghost": r"""
  \
   \  .-.
     (o o)
     | O |
      \ \_
       `--'
"""
}

def metadata():
    return {
        "name": "cowsay",
        "version": "1.0.0",
        "description": "Configurable speaking ASCII cow and creatures",
        "author": "FractalOS Community",
        "license": "MIT",
        "wheels": [],
        "dependencies": []
    }

def define_flags():
    return {
        "flags": [
            {"name": "help", "short": "h", "long": "help", "takes_value": False},
            {"name": "file", "short": "f", "long": "file", "takes_value": True},
            {"name": "width", "short": "W", "long": "width", "takes_value": True},
            {"name": "borg", "short": "b", "long": "borg", "takes_value": False},
            {"name": "dead", "short": "d", "long": "dead", "takes_value": False},
            {"name": "greedy", "short": "g", "long": "greedy", "takes_value": False},
            {"name": "paranoid", "short": "p", "long": "paranoid", "takes_value": False},
            {"name": "stoned", "short": "s", "long": "stoned", "takes_value": False},
            {"name": "tired", "short": "t", "long": "tired", "takes_value": False},
            {"name": "wired", "short": "w", "long": "wired", "takes_value": False},
            {"name": "youthful", "short": "y", "long": "youthful", "takes_value": False},
            {"name": "think", "short": "T", "long": "think", "takes_value": False},
        ],
        "aliases": {
            "h": "help", "f": "file", "W": "width",
            "b": "borg", "d": "dead", "g": "greedy",
            "p": "paranoid", "s": "stoned", "t": "tired",
            "w": "wired", "y": "youthful", "T": "think"
        }
    }

import re

def _strip_ansi(s):
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', s)

def _visible_len(s):
    return len(_strip_ansi(s))

def _build_bubble(lines, think=False):
    max_len = max(_visible_len(l) for l in lines) if lines else 0
    border_top = " " + "_" * (max_len + 2)
    border_bot = " " + "-" * (max_len + 2)
    
    bubble_lines = [border_top]
    
    if len(lines) == 1:
        start_char, end_char = ("( ", " )") if think else ("< ", " >")
        pad = " " * (max_len - _visible_len(lines[0]))
        bubble_lines.append(f"{start_char}{lines[0]}{pad}{end_char}")
    else:
        for idx, line in enumerate(lines):
            pad = " " * (max_len - _visible_len(line))
            padded = f"{line}{pad}"
            if think:
                bubble_lines.append(f"( {padded} )")
            elif idx == 0:
                bubble_lines.append(f"/ {padded} \\")
            elif idx == len(lines) - 1:
                bubble_lines.append(f"\\ {padded} /")
            else:
                bubble_lines.append(f"| {padded} |")
                
    bubble_lines.append(border_bot)
    return "\n".join(bubble_lines)

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    if flags.get("help"):
        return {"success": True, "output": help(args, flags, user_context)}

    # Resolve message
    if args:
        raw_msg = " ".join(args)
    elif stdin_data is not None and str(stdin_data).strip():
        raw_msg = str(stdin_data).strip()
    else:
        raw_msg = "Moo! Welcome to FractalOS."

    # Wrapping
    width = 40
    if flags.get("width"):
        try:
            width = max(10, int(flags.get("width")))
        except ValueError:
            pass

    lines = []
    for paragraph in raw_msg.splitlines():
        if not paragraph.strip():
            lines.append("")
        else:
            wrapped = textwrap.wrap(paragraph, width=width)
            lines.extend(wrapped or [""])
    if not lines:
        lines = [" "]

    # Expression
    eyes = "oo"
    tongue = "  "
    if flags.get("borg"):
        eyes = "=="
    elif flags.get("dead"):
        eyes = "xx"
        tongue = "U "
    elif flags.get("greedy"):
        eyes = "$$"
    elif flags.get("paranoid"):
        eyes = "@@"
    elif flags.get("stoned"):
        eyes = "**"
    elif flags.get("tired"):
        eyes = "--"
    elif flags.get("wired"):
        eyes = "OO"
    elif flags.get("youthful"):
        eyes = ".."

    think = bool(flags.get("think"))
    bubble = _build_bubble(lines, think=think)

    cow_choice = flags.get("file", "default")
    template = COWS.get(cow_choice, COWS["default"])

    # If think mode, replace speech slashes with bubbles
    if think:
        template = template.replace(r"\   ^__^", r"o   ^__^").replace(r" \  (", r"  o (").replace(r" \ ", r" o ")

    rendered_cow = template.format(eyes=eyes, tongue=tongue)
    return f"{bubble}{rendered_cow}"

def man(args, flags, user_context, **kwargs):
    return """
NAME
    cowsay - Configurable speaking ASCII cow and creatures

SYNOPSIS
    cowsay [-f creature] [-b|-d|-g|-p|-s|-t|-w|-y] [-W width] [-T] [message...]

DESCRIPTION
    Generates an ASCII picture of a cow (or other creatures) saying or thinking
    the specified message, wrapped nicely in a speech bubble.

OPTIONS
    -f creature
        Select creature template: default, tux, duck, ghost.
    -W width
        Maximum message wrap column width (default: 40).
    -T, --think
        Use thought bubble instead of speech.
    -b  Borg mode (==)
    -d  Dead mode (xx)
    -g  Greedy mode ($$)
    -p  Paranoid mode (@@)
    -s  Stoned mode (**)
    -t  Tired mode (--)
    -w  Wired mode (OO)
    -y  Youthful mode (..)

EXAMPLES
    cowsay "Hello FractalOS!"
    fortune | cowsay
    fortune | cowsay -f tux -w
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: cowsay [-f creature] [-b|-d|-g|-p|-s|-t|-w|-y] [-W width] [-T] [message...]"
