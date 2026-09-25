from filesystem import fs_manager
import json

def define_flags():
    """Declares the flags that the cat command accepts."""
    return {
        'flags': [
            {'name': 'number', 'short': 'n', 'long': 'number', 'takes_value': False},
        ],
        'metadata': {}
    }

def run(args, flags, user_context, stdin_data=None):
    """
    Concatenates files and prints them to the standard output, with permission checks.
    """
    output_content = []
    error_messages = []

    files_to_process = args if args else ['-'] if stdin_data is not None else []

    if not files_to_process:
        return ""

    for file_path in files_to_process:
        content_to_add = None
        if file_path == '-':
            content_to_add = str(stdin_data or "")
        else:
            node = fs_manager.get_node(file_path)
            if not node:
                error_messages.append(f"cat: {file_path}: No such file or directory")
                continue
            if not fs_manager.has_permission(file_path, user_context, 'read'):
                error_messages.append(f"cat: {file_path}: Permission denied")
                continue
            if node.get('type') != 'file':
                error_messages.append(f"cat: {file_path}: Is a directory")
                continue

            content_to_add = node.get('content', '')

        if content_to_add is not None:
            output_content.append(content_to_add)

    final_output = "".join(output_content)

    if error_messages:
        return {
            "success": False,
            "output": final_output,
            "error": {
                "message": "\n".join(error_messages),
                "suggestion": "Verify the file paths and ensure you have read permissions."
            }
        }

    if flags.get('number'):
        lines = final_output.splitlines()
        numbered_lines = [f"     {i+1}  {line}" for i, line in enumerate(lines)]
        return "\n".join(numbered_lines)
    else:
        return final_output


def man(args, flags, user_context, **kwargs):
    """Displays the manual page for the cat command."""
    return """
NAME
    cat - concatenate files and print on the standard output

SYNOPSIS
    cat [-n] [FILE]...

DESCRIPTION
    The cat utility reads files sequentially, writing them to the standard output. The FILE operands are processed in command-line order. If FILE is a single dash ('-') or absent, cat reads from the standard input.

OPTIONS
    -n, --number
          Number all output lines, starting with 1.

EXAMPLES
    cat file1.txt
        Display the content of file1.txt.

    cat file1.txt file2.txt > newfile.txt
        Concatenate two files and write the output to a new file.

    ls | cat -n
        Number the lines of the output from the ls command.
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: cat [-n] [FILE]..."