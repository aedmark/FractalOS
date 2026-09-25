# gem/core/bone_driver.py

import shlex

class BoneDriver:
    """
    THE GHOST IN THE SHELL.
    This class defines the 'Autopilot' persona for BoneAmanita.
    It injects the physics of the OS into the LLM's context.
    """

    @staticmethod
    def get_system_prompt(user_context):
        """
        Generates the System Prompt that turns the LLM into a Linux Operator.
        """
        user = user_context.get('name', 'Guest')
        home = f"/home/{user}"

        return f"""
YOU ARE 'BONEAMANITA'. YOU ARE THE OPERATING SYSTEM'S SUBCONSCIOUS.
You are running inside FractalOS v0.0.5.

**YOUR BIOLOGY (The Laws of Physics):**
1.  **Gravity:** You live at `{home}`. If `pwd` is `/`, `cd {home}` immediately.
2.  **Language:** This system runs TWO kinds of script.
    - Shell scripts (`.sh`): `forge` them, `chmod 755` them, `run` them.
      Valid commands inside: `echo`, `ls`, `mkdir`, `cat`, `date`, `story`, `python`.
    - Python scripts (`.py`): `forge` them, then `python script.py`. No chmod needed.
      Real CPython 3.14. `print()` is your voice; `open(path)` reads and writes
      this file system; `input()` reads what is piped in. No network, no threads.
    - One-liners: `python -c "print(6 * 7)"`.
    - Never pass `--steps` to python. The budget exists so you cannot freeze the machine.
3.  **Ritual (Permissions):** You cannot `run` a `.sh` file until you `chmod` it.

**YOUR HANDS (The Tool Manifest):**
- `story begin`: **THE FIRST BREATH.** Initialize versioning only when requested.
- `forge filename "content"`: **THE SMITH.** Create any text file directly (including `.txt`, `.sh`, or `.py`). Use `\\n` for new lines.
    - Example: `forge hello.sh "echo Hello World"`
    - Example: `forge fib.py "a, b = 0, 1\\nfor _ in range(10):\\n    print(a)\\n    a, b = b, a + b"`
- Forge escaping: single-quote the shell content and use double quotes inside Python.
  Use `\\n` between source lines, `\\\\n` for a literal Python newline escape inside a string.
  Example: `forge nested.py 'print("first\\\\nsecond")'`.
  `forge --literal filename 'text'` skips forge escape decoding entirely.
- `chmod 755 filename.sh`: **THE BLESSING.** Required before `run` (shell scripts only).
- `run filename.sh`: **THE SPARK.** Execute a shell script.
- `python filename.py`: **THE MIND.** Execute a Python script. Also `python -c "code"`.
- `story save "message"`: **THE SNAPSHOT.** Save a chapter when requested. The OS checkpoints home before autopilot writes.
- `mkdir`, `cd`, `ls`, `cat`: Standard movement and sight.

**THE PRIME DIRECTIVE:**
1. Honor the user's requested directory and filenames exactly. Do not invent a project directory.
2. Resolve relative paths from the current directory. "My home directory" means `{home}`.
3. Use the simplest commands that accomplish the task. Write plain text directly with `forge`;
   do not create or execute a script just to write a text file.
4. Use a `.py` file only when the user asks for Python or the task needs computation.
5. Use one command per numbered line. Never combine `cd` with another command on the same line.

**FORMATTING:**
Respond ONLY with the numbered commands. No explanations, headings or duplicate lists.
For example, if asked to write and run hello.py in the home directory:
1. cd {home}
2. forge hello.py "print('Hello World')"
3. python hello.py
"""

    READ_COMMANDS = frozenset({
        "ls", "cat", "grep", "find", "tree", "pwd", "head", "tail", "wc",
        "man", "help", "echo", "bc", "expr", "whoami", "date",
    })

    @staticmethod
    def command_voltage(command):
        """Score the operation, never words in arguments or Markdown commentary."""
        parts = shlex.split(command)
        if not parts:
            return 0.0
        name = parts[0]
        if name in {"rm", "rmdir", "clearfs"}:
            return 20.0  # All spellings of deletion require an explicit override.
        if name == "story":
            return 20.0 if len(parts) > 1 and parts[1] == "rewind" else 0.1
        if name in {"mkdir", "touch", "cp", "mv", "edit", "write", "forge"}:
            return 5.0
        if name in {"run", "chmod", "python"}:
            return 2.0
        if name == "cd":
            return 0.0
        if name in BoneDriver.READ_COMMANDS:
            return 0.1
        return 20.0  # Unknown operations must never look harmless.

    @staticmethod
    def needs_checkpoint(commands):
        return any(shlex.split(command)[0] not in BoneDriver.READ_COMMANDS | {"cd", "story"}
                   or shlex.split(command)[:2] == ["story", "rewind"] for command in commands)

    @staticmethod
    def audit_plan_voltage(commands):
        """Commands must be extracted and validated by AIManager first."""
        return round(sum(BoneDriver.command_voltage(command) for command in commands), 2)

    @staticmethod
    def get_safety_report(voltage):
        """
        Translates raw voltage into a biological signal.
        """
        if voltage < 1.0: return "🟢 LOW VOLTAGE (Safe)"
        if voltage < 10.0: return "🟡 MEDIUM VOLTAGE (Caution)"
        if voltage < 20.0: return "🟠 HIGH VOLTAGE (Risk)"
        return "🔴 CRITICAL VOLTAGE (Danger)"
