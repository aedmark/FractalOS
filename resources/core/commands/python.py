# /core/commands/python.py
#
# Run real Python inside FractalOS. The kernel already *is* CPython (under
# Pyodide), so a script runs in the same interpreter as the OS, with:
#   - stdout and stderr captured and returned as command output,
#   - open() and input() rewired to the FractalOS virtual file system and to
#     the command's stdin pipe (see D-011),
#   - a step budget so a runaway loop cannot freeze the page (the kernel runs
#     on the browser's main thread; nothing can interrupt it otherwise).
#
# It is not a sandbox. A script has the same trust as any other shell command:
# it can import kernel modules from /core and break things on purpose.

import builtins
import contextlib
import io
import os
import sys
import traceback

from filesystem import fs_manager

DEFAULT_STEP_BUDGET = 2_000_000   # line events; --steps 0 disables the budget
SCRIPT_FILENAME = "<python>"


def define_flags():
    """Declares the flags that the python command accepts."""
    return {
        'flags': [
            {'name': 'code', 'short': 'c', 'long': 'code', 'takes_value': True,
             'description': 'Run this string instead of a file.'},
            {'name': 'steps', 'long': 'steps', 'takes_value': True,
             'description': f'Line-event budget before the script is stopped (default {DEFAULT_STEP_BUDGET}, 0 = unlimited).'},
        ],
        'metadata': {}
    }


class StepBudgetExceeded(RuntimeError):
    pass


class _VfsTextFile(io.StringIO):
    """A text file backed by the virtual file system. Written back on close."""

    def __init__(self, path, mode, user_context, initial=""):
        super().__init__(initial)
        self._path = path
        self._mode = mode
        self._user_context = user_context
        self._writable = any(m in mode for m in "wax+")
        self._readable = 'r' in mode or '+' in mode
        self._dirty = False
        if 'a' in mode:
            self.seek(0, io.SEEK_END)
        self.name = path

    def readable(self):
        return self._readable

    def writable(self):
        return self._writable

    def read(self, *args):
        if not self._readable:
            raise io.UnsupportedOperation("not readable")
        return super().read(*args)

    def readline(self, *args):
        if not self._readable:
            raise io.UnsupportedOperation("not readable")
        return super().readline(*args)

    def write(self, s):
        if not self._writable:
            raise io.UnsupportedOperation("not writable")
        self._dirty = True
        return super().write(s)

    def flush(self):
        if self._writable and self._dirty and not self.closed:
            fs_manager.write_file(self._path, self.getvalue(), self._user_context)
            self._dirty = False

    def close(self):
        if not self.closed:
            self.flush()
            super().close()

    def __del__(self):
        # CPython refcounting closes a dropped file object at once, so
        # open(p, 'w').write(s) without close() still lands in the VFS.
        try:
            self.close()
        except Exception:
            pass


def _make_open(user_context):
    def vfs_open(file, mode='r', *args, **kwargs):
        mode = str(mode)
        if 'b' in mode:
            raise ValueError("python: the FractalOS file system is text-only; binary modes are not supported")
        path = fs_manager.get_absolute_path(str(file))
        node = fs_manager.get_node(path)
        wants_read = 'r' in mode or '+' in mode
        wants_write = any(m in mode for m in "wax+")

        if node is not None and node.get('type') != 'file':
            raise IsADirectoryError(21, "Is a directory", path)
        if 'x' in mode and node is not None:
            raise FileExistsError(17, "File exists", path)
        if node is None:
            if not wants_write or 'r' in mode:
                raise FileNotFoundError(2, "No such file or directory", path)
            parent = os.path.dirname(path)
            if not fs_manager.get_node(parent):
                raise FileNotFoundError(2, "No such file or directory", parent)
            if not fs_manager.has_permission(parent, user_context, 'write'):
                raise PermissionError(13, "Permission denied", path)
            return _VfsTextFile(path, mode, user_context, "")

        if wants_read and not fs_manager.has_permission(path, user_context, 'read'):
            raise PermissionError(13, "Permission denied", path)
        if wants_write and not fs_manager.has_permission(path, user_context, 'write'):
            raise PermissionError(13, "Permission denied", path)

        keep_content = 'a' in mode or ('+' in mode and 'w' not in mode)
        initial = node.get('content', '') if (wants_read or keep_content) else ""
        if 'w' in mode:
            initial = ""
        return _VfsTextFile(path, mode, user_context, initial)
    return vfs_open


def _make_input(stdin_lines, out):
    def vfs_input(prompt=''):
        if prompt:
            out.write(str(prompt))
        try:
            return next(stdin_lines)
        except StopIteration:
            raise EOFError("python: input() ran out of stdin. Pipe it in: echo 42 | python script.py")
    return vfs_input


def _make_tracer(budget):
    count = 0

    def tracer(frame, event, arg):
        nonlocal count
        if event == 'line':
            count += 1
            if count > budget:
                raise StepBudgetExceeded(budget)
        return tracer
    return tracer


def _format_user_traceback(exc):
    """The traceback from the script's frames only, not this module's."""
    tb = exc.__traceback__
    here = os.path.normpath(__file__) if '__file__' in globals() else None
    while tb is not None and here and os.path.normpath(tb.tb_frame.f_code.co_filename) == here:
        tb = tb.tb_next
    return "".join(traceback.format_exception(type(exc), exc, tb))


def _fail(message, suggestion, output=""):
    return {
        "success": False,
        "output": output,
        "error": {"message": message, "suggestion": suggestion}
    }


def run(args, flags, user_context, stdin_data=None, **kwargs):
    code_flag = flags.get('code')
    steps_flag = flags.get('steps')

    # --- What to run ---
    if code_flag is not None:
        source, filename, argv = str(code_flag), "<-c>", ["-c"] + list(args)
    elif args and args[0] != '-':
        script_path = args[0]
        validation = fs_manager.validate_path(
            script_path, user_context, '{"expectedType": "file", "permissions": ["read"]}')
        if not validation.get("success"):
            return _fail(f"python: can't open '{script_path}': {validation.get('error')}",
                         "Check the path, and that you can read the file.")
        source = validation["node"].get('content', '')
        filename = validation["resolvedPath"]
        argv = [filename] + list(args[1:])
    elif stdin_data is not None:
        source, filename, argv = str(stdin_data), "<stdin>", ["-"] + list(args[1:] if args else [])
    else:
        return _fail("python: nothing to run.",
                     "Give me a file ('python script.py'), some code ('python -c \"print(1)\"'), or pipe code in.")

    if steps_flag is not None:
        try:
            budget = int(steps_flag)
            if budget < 0:
                raise ValueError
        except ValueError:
            return _fail(f"python: --steps wants a whole number, not '{steps_flag}'.",
                         "Try --steps 5000000, or --steps 0 for no limit.")
    else:
        budget = DEFAULT_STEP_BUDGET

    try:
        compiled = compile(source, filename, 'exec')
    except SyntaxError as e:
        return _fail("".join(traceback.format_exception_only(type(e), e)).rstrip(),
                     "That's not Python. Well, not yet.")

    # --- The script's world ---
    out = io.StringIO()
    stdin_text = "" if stdin_data is None or filename == "<stdin>" else str(stdin_data)
    script_builtins = dict(builtins.__dict__)
    script_builtins['open'] = _make_open(user_context)
    script_builtins['input'] = _make_input(iter(stdin_text.splitlines()), out)
    script_globals = {
        '__name__': '__main__',
        '__file__': filename,
        '__builtins__': script_builtins,
    }

    saved_argv, saved_stdin = sys.argv, sys.stdin
    sys.argv = argv
    sys.stdin = io.StringIO(stdin_text)
    exit_status = 0
    error = None
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            if budget:
                sys.settrace(_make_tracer(budget))
            try:
                exec(compiled, script_globals)
            finally:
                sys.settrace(None)
    except SystemExit as e:
        code = e.code
        if code is None or code == 0:
            exit_status = 0
        elif isinstance(code, int):
            exit_status = code
        else:
            out.write(f"{code}\n")
            exit_status = 1
    except StepBudgetExceeded as e:
        error = (f"python: stopped after {e.args[0]:,} steps. That looks like a loop that never ends.",
                 "If it really needs more, run it with --steps N (or --steps 0 for no limit) and good luck.")
    except BaseException as e:  # noqa: BLE001 - anything the script raised is the script's problem, reported, not ours
        error = (_format_user_traceback(e).rstrip(), "The traceback above is from your script.")
    finally:
        sys.argv, sys.stdin = saved_argv, saved_stdin
        sys.settrace(None)

    output = out.getvalue()
    if output.endswith("\n"):
        output = output[:-1]

    if error:
        message, suggestion = error
        full = f"{output}\n{message}" if output else message
        return _fail(full, suggestion, output)
    if exit_status:
        full = f"{output}\npython: exit status {exit_status}" if output else f"python: exit status {exit_status}"
        return _fail(full, "The script asked to exit with a non-zero status.", output)
    return {"success": True, "output": output}


def man(args, flags, user_context, **kwargs):
    return f"""
NAME
    python - run real Python, right here, inside FractalOS

SYNOPSIS
    python SCRIPT [ARGS...]
    python -c "CODE" [ARGS...]
    ... | python

DESCRIPTION
    Runs a Python script in the same CPython {sys.version.split()[0]} interpreter that the
    FractalOS kernel runs in (under Pyodide). Anything printed comes back as the
    command's output, so it pipes and redirects like any other command.

    Inside a script:
      open(path, mode)   reads and writes files in the FractalOS file system,
                         honouring its permissions. Text modes only ('r', 'w',
                         'a', 'x', '+'); no 'b'. Relative paths start at the
                         shell's current directory. Files are written back when
                         closed (a 'with' block, .close(), or letting the object go).
      input()            reads a line from what was piped in.
      sys.argv           is the script path followed by ARGS.
      sys.exit(n)        ends the script; a non-zero n makes the command fail.

    A script is stopped after {DEFAULT_STEP_BUDGET:,} line steps so a loop that never
    ends cannot freeze the whole OS. Raise or remove the limit with --steps.

OPTIONS
    -c, --code CODE   Run CODE instead of a file.
    --steps N         Step budget (0 = unlimited).

LIMITATIONS
    This is the kernel's own interpreter, not a sandbox: a script can import
    the kernel's modules and change things it should not. Only open() in the
    script itself talks to the FractalOS file system; the standard library
    (pathlib, os, shutil, json.load on a real path) sees Pyodide's private
    file system instead, where /core lives. There are no threads, no
    subprocesses and no network sockets; use pyodide.http for HTTP.

EXAMPLES
    python -c "print(2 ** 64)"
    echo "print(open('notes.txt').read().upper())" > shout.py; python shout.py
    python -c "import sys; print(sys.argv[1:])" one two
    echo 21 | python -c "print(int(input()) * 2)"
    python -c "open('log.txt', 'a').write('hello\\n')"
"""


def help(args, flags, user_context, **kwargs):
    return 'Usage: python SCRIPT [ARGS...]  |  python -c "CODE"  |  ... | python'
