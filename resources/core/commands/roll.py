# gemini/core/commands/roll.py

import random
import re

def define_flags():
    """Declares the flags that the roll command accepts."""
    return {'flags': [], 'metadata': {}}

def run(args, flags, user_context, **kwargs):
    """
    Rolls dice based on standard D&D notation (e.g., 1d20, 3d6+4).
    """
    if not args:
        return {"success": False, "error": {"message": "roll: missing dice notation", "suggestion": "Usage: roll <notation>, e.g., 'roll 1d20' or 'roll 2d8+5'"}}

    dice_string = "".join(args).lower()

    # Regex to parse notation like '3d6+4' or '1d20-1'
    match = re.match(r'(\d+)d(\d+)([+-]\d+)?', dice_string)

    if not match:
        return {"success": False, "error": {"message": f"roll: invalid dice notation '{dice_string}'", "suggestion": "Use format like '1d20', '3d6', or '2d10+4'."}}

    num_dice = int(match.group(1))
    num_sides = int(match.group(2))
    modifier_str = match.group(3)

    if num_dice <= 0 or num_sides <= 0:
        return {"success": False, "error": {"message": "roll: number of dice and sides must be positive"}}

    if num_dice > 100:
        return {"success": False, "error": {"message": "roll: cannot roll more than 100 dice at once"}}

    rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
    total = sum(rolls)

    modifier = 0
    if modifier_str:
        modifier = int(modifier_str)
        total += modifier

    # Build the output string
    rolls_str = " + ".join(map(str, rolls))

    if len(rolls) > 1:
        output = f"Rolling {dice_string}...\n  - Rolls: ({rolls_str})\n"
    else:
        output = f"Rolling {dice_string}...\n"

    if modifier_str:
        output += f"  - Modifier: {modifier_str}\n"

    output += f"  - Total: {total}"

    return output

def man(args, flags, user_context, **kwargs):
    return """
NAME
roll - a utility for rolling polyhedral dice.

SYNOPSIS
roll <notation>

DESCRIPTION
Rolls dice based on standard tabletop RPG notation (e.g., XdY+Z). It shows the individual rolls, the modifier, and the final total.

EXAMPLES:
roll 1d20
roll 3d6
roll 2d8+5
roll 1d100-10
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: roll <notation> (e.g., '1d20', '3d6+4')"