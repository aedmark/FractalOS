import os
from filesystem import fs_manager

def define_flags():
    """Declares the flags that the tree command accepts."""
    return {
        'flags': [
            {'name': 'level', 'short': 'L', 'long': 'level', 'takes_value': True},
            {'name': 'dirs-only', 'short': 'd', 'long': 'dirs-only', 'takes_value': False},
            {'name': 'color', 'short': 'C', 'long': 'color', 'takes_value': False},
        ],
        'metadata': {}
    }

def run(args, flags, user_context, **kwargs):
    path_arg = args[0] if args else "."
    start_path = fs_manager.get_absolute_path(path_arg)
    start_node = fs_manager.get_node(start_path)

    if not start_node:
        return {
            "success": False,
            "error": {
                "message": f"tree: '{path_arg}' [error opening dir]",
                "suggestion": "The specified directory does not exist or cannot be accessed."
            }
        }
    if start_node.get('type') != 'directory':
        return {
            "success": False,
            "error": {
                "message": f"tree: '{path_arg}' is not a directory.",
                "suggestion": "The tree command can only be used on directories."
            }
        }

    try:
        max_depth = int(flags.get('level')) if flags.get('level') else float('inf')
        if max_depth <= 0:
            return {
                "success": False,
                "error": {
                    "message": f"tree: Invalid level, must be greater than 0.",
                    "suggestion": "Please provide a positive integer for the level."
                }
            }
    except (ValueError, TypeError):
        return {
            "success": False,
            "error": {
                "message": "tree: Invalid level, must be an integer.",
                "suggestion": "Please provide a whole number for the level."
            }
        }


    dirs_only = flags.get('dirs-only', False)
    use_color = flags.get('color', False)

    def paint(name, node):
        # Like tree -C with the usual LS_COLORS: directories bold blue, symlinks bold cyan,
        # executable files bold green, everything else plain.
        if not use_color:
            return name
        kind = node.get('type')
        if kind == 'directory':
            code = "1;34"
        elif kind == 'symlink':
            code = "1;36"
        elif int(node.get('mode', 0) or 0) & 0o111:
            code = "1;32"
        else:
            return name
        return f"\x1b[{code}m{name}\x1b[0m"

    output, dir_count, file_count = [paint(path_arg, start_node)], 0, 0

    def build_tree(node, prefix="", current_depth=0):
        nonlocal dir_count, file_count
        if current_depth >= max_depth: return

        children = sorted(node.get('children', {}).keys())
        for i, name in enumerate(children):
            child_node = node['children'][name]
            is_last = (i == len(children) - 1)
            connector = "└── " if is_last else "├── "
            new_prefix = prefix + ("    " if is_last else "│   ")

            if child_node.get('type') == 'directory':
                dir_count += 1
                output.append(f"{prefix}{connector}{paint(name, child_node)}")
                build_tree(child_node, new_prefix, current_depth + 1)
            elif not dirs_only:
                file_count += 1
                output.append(f"{prefix}{connector}{paint(name, child_node)}")

    build_tree(start_node)

    summary = f"\n{dir_count} director{'y' if dir_count == 1 else 'ies'}"
    if not dirs_only: summary += f", {file_count} file{'s' if file_count != 1 else ''}"
    output.append(summary)

    return "\n".join(output)

def man(args, flags, user_context, **kwargs):
    return """
NAME
    tree - list contents of directories in a tree-like format

SYNOPSIS
    tree [-d] [-C] [-L level] [DIRECTORY]

DESCRIPTION
    Recursively displays the directory structure of a given path in a
    tree-like format. If no directory is specified, it lists the
    current directory.

OPTIONS
    -d
        List directories only.
    -L level
        Descend only 'level' directories deep.
    -C
        Colour the names: directories blue, symlinks cyan, executables
        green. The colour codes travel with the text, so they end up in
        pipes and files too, same as the real thing.

EXAMPLES
    tree
    tree /home/guest
    tree -L 2 -d
    tree -C ~
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: tree [-d] [-C] [-L level] [DIRECTORY]"