"""
banner - Print large ASCII banner text
"""

# 5-line high character glyphs (A-Z, 0-9, punctuation)
FONT_5 = {
    'A': [
        " ### ",
        "#   #",
        "#####",
        "#   #",
        "#   #"
    ],
    'B': [
        "#### ",
        "#   #",
        "#### ",
        "#   #",
        "#### "
    ],
    'C': [
        " ####",
        "#    ",
        "#    ",
        "#    ",
        " ####"
    ],
    'D': [
        "#### ",
        "#   #",
        "#   #",
        "#   #",
        "#### "
    ],
    'E': [
        "#####",
        "#    ",
        "#### ",
        "#    ",
        "#####"
    ],
    'F': [
        "#####",
        "#    ",
        "#### ",
        "#    ",
        "#    "
    ],
    'G': [
        " ####",
        "#    ",
        "# ###",
        "#   #",
        " ####"
    ],
    'H': [
        "#   #",
        "#   #",
        "#####",
        "#   #",
        "#   #"
    ],
    'I': [
        "#####",
        "  #  ",
        "  #  ",
        "  #  ",
        "#####"
    ],
    'J': [
        "  ###",
        "    #",
        "    #",
        "#   #",
        " ### "
    ],
    'K': [
        "#   #",
        "#  # ",
        "###  ",
        "#  # ",
        "#   #"
    ],
    'L': [
        "#    ",
        "#    ",
        "#    ",
        "#    ",
        "#####"
    ],
    'M': [
        "#   #",
        "## ##",
        "# # #",
        "#   #",
        "#   #"
    ],
    'N': [
        "#   #",
        "##  #",
        "# # #",
        "#  ##",
        "#   #"
    ],
    'O': [
        " ### ",
        "#   #",
        "#   #",
        "#   #",
        " ### "
    ],
    'P': [
        "#### ",
        "#   #",
        "#### ",
        "#    ",
        "#    "
    ],
    'Q': [
        " ### ",
        "#   #",
        "#   #",
        "#  ##",
        " ####"
    ],
    'R': [
        "#### ",
        "#   #",
        "#### ",
        "#  # ",
        "#   #"
    ],
    'S': [
        " ####",
        "#    ",
        " ### ",
        "    #",
        "#### "
    ],
    'T': [
        "#####",
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  "
    ],
    'U': [
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        " ### "
    ],
    'V': [
        "#   #",
        "#   #",
        "#   #",
        " # # ",
        "  #  "
    ],
    'W': [
        "#   #",
        "#   #",
        "# # #",
        "## ##",
        "#   #"
    ],
    'X': [
        "#   #",
        " # # ",
        "  #  ",
        " # # ",
        "#   #"
    ],
    'Y': [
        "#   #",
        " # # ",
        "  #  ",
        "  #  ",
        "  #  "
    ],
    'Z': [
        "#####",
        "   # ",
        "  #  ",
        " #   ",
        "#####"
    ],
    '0': [
        " ### ",
        "#  ##",
        "# # #",
        "##  #",
        " ### "
    ],
    '1': [
        "  #  ",
        " ##  ",
        "  #  ",
        "  #  ",
        " ### "
    ],
    '2': [
        " ### ",
        "    #",
        " ### ",
        "#    ",
        "#####"
    ],
    '3': [
        "#### ",
        "    #",
        " ### ",
        "    #",
        "#### "
    ],
    '4': [
        "#  # ",
        "#  # ",
        "#####",
        "   # ",
        "   # "
    ],
    '5': [
        "#####",
        "#    ",
        "#### ",
        "    #",
        "#### "
    ],
    '6': [
        " ### ",
        "#    ",
        "#### ",
        "#   #",
        " ### "
    ],
    '7': [
        "#####",
        "    #",
        "   # ",
        "  #  ",
        "  #  "
    ],
    '8': [
        " ### ",
        "#   #",
        " ### ",
        "#   #",
        " ### "
    ],
    '9': [
        " ### ",
        "#   #",
        " ####",
        "    #",
        " ### "
    ],
    ' ': [
        "   ",
        "   ",
        "   ",
        "   ",
        "   "
    ],
    '!': [
        " # ",
        " # ",
        " # ",
        "   ",
        " # "
    ],
    '?': [
        "### ",
        "   #",
        " ## ",
        "    ",
        " ## "
    ],
    '-': [
        "     ",
        "     ",
        "#####",
        "     ",
        "     "
    ],
    '+': [
        "  #  ",
        "  #  ",
        "#####",
        "  #  ",
        "  #  "
    ],
    '.': [
        "   ",
        "   ",
        "   ",
        "   ",
        " # "
    ],
    ':': [
        "   ",
        " # ",
        "   ",
        " # ",
        "   "
    ],
}

def metadata():
    return {
        "name": "banner",
        "version": "1.0.0",
        "description": "Prints large ASCII banner letters",
        "author": "FractalOS Community",
        "license": "MIT",
        "wheels": [],
        "dependencies": []
    }

def define_flags():
    return {
        "flags": [
            {"name": "help", "short": "h", "long": "help", "takes_value": False},
            {"name": "char", "short": "c", "long": "char", "takes_value": True},
        ],
        "aliases": {
            "h": "help", "c": "char"
        }
    }

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    if flags.get("help"):
        return {"success": True, "output": help(args, flags, user_context)}

    if args:
        text = " ".join(args)
    elif stdin_data is not None and str(stdin_data).strip():
        text = str(stdin_data).strip()
    else:
        text = "FRACTAL"

    fill_char = flags.get("char", "#")
    if len(fill_char) > 1:
        fill_char = fill_char[0]

    text = text.upper()
    lines = ["", "", "", "", ""]

    for char in text:
        glyph = FONT_5.get(char)
        if not glyph:
            glyph = FONT_5.get('?')
        for row in range(5):
            glyph_row = glyph[row]
            if fill_char != '#':
                glyph_row = glyph_row.replace('#', fill_char)
            lines[row] += glyph_row + "  "

    return "\n" + "\n".join(line.rstrip() for line in lines) + "\n"

def man(args, flags, user_context, **kwargs):
    return """
NAME
    banner - Print large ASCII banner text

SYNOPSIS
    banner [-c char] [text...]

DESCRIPTION
    Generates a high-visibility 5-line banner display of the input text
    using ASCII characters.

OPTIONS
    -c char
        Fill character to use for rendering glyphs (default: '#').

EXAMPLES
    banner FRACTAL
    banner -c '*' "HELLO OS"
    date | banner
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: banner [-c char] [text...]"
