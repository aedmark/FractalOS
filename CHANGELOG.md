# CHANGELOG.md

## [Unreleased] - BoneAmanita Integration

### 🚀 New Features (The Kinetic Engine)
- **The agent can use `python`:** whitelisted; in agent mode the user confirms it first (like `forge` and `rm`); the autopilot persona now describes `.py` scripts and `python -c` one-liners; the agent may not pass `--steps`.
- **New Command: `python`** (`resources/core/commands/python.py`): run real Python inside FractalOS. `python script.py [args]`, `python -c "code"`, or `... | python`. Runs in the kernel's own CPython 3.14 (Pyodide); stdout/stderr come back as command output; `open()` reads and writes the FractalOS file system with its permissions; `input()` reads the pipe; `sys.argv` and `sys.exit()` behave; a step budget (`--steps`, default 2,000,000) stops runaway loops so the page cannot freeze. Not a sandbox (same trust as any command).
- **BoneAmanita Autopilot:** Integrated a state-aware, kinetic AI driver accessible via `gemini --autopilot`.
    - **The Switch:** Added `--autopilot` (`-a`) and `--force` (`-f`) flags to the `gemini` command.
    - **The Brain:** Created `bone_driver.py` to handle system prompting, physics injection, and safety auditing.
    - **The Conscience:** implemented "Voltage" metrics to assess the risk of AI plans (e.g., `rm` is High Voltage, `ls` is Low Voltage).
    - **The Loop:** `ai_manager.py` now supports "Stateless Memory Injection," allowing the AI to remember `cd` changes across execution steps.

- **New Command: `forge`**
    - A specialized file-writing tool (`resources/core/commands/forge.py`) designed for AI use.
    - Supports atomic writes and newline expansion (`\n`) to replace the clumsy `echo` redirection for code generation.

### ⚡ System Improvements
- **Agent harness:** `node tests/agent.js` drives `gemini --autopilot` and `gemini "<prompt>"` through seven tasks against a real Ollama (or `tests/fake_ollama.py`, a stand-in that proves the plumbing without a model), auto-confirms the permission dialog, grades outcomes on the file system, and writes `tests/out/agent-transcript.md` with every prompt, answer and timing.
- **Pyodide Upgrade & Trim:** Updated the vendored Pyodide runtime in `resources/dep/pyodide/` from 0.28.0.dev0 (Python 3.13) to 314.0.7 (Python 3.14.2), and trimmed it from ~415 MB / 413 files to ~16 MB / 9 files: the core runtime (`pyodide.js`, `pyodide.asm.mjs`, `pyodide.asm.wasm`, `python_stdlib.zip`, `pyodide-lock.json`) plus only the wheels the kernel loads (`cryptography` and its dependencies `cffi`, `pycparser`, `six`). `ssl` and `hashlib` are now built into the core runtime, so `bridge.js` no longer requests the `ssl` package.
- **Expanded Whitelist:** Updated `ai_manager.py` to allow the AI to use `forge`, `run`, `chmod`, and `python`.
- **Manifest Update:** Updated `resources/bridge.js` to include `bone_driver` in the Python Kernel boot sequence.
- **Safety Calibration:** Tuned the "Voltage" costs to distinguish between "Creation" (High Cost) and "Execution" (Medium Cost), enabling smoother developer workflows.

### 🐛 Bug Fixes
- **The agent always thought it was in `/`:** its context probe (`pwd`, `ls -la`) ran without a current path, which reset the kernel's working directory to the root before the model was asked for a plan. Every plan was sensed from, and driven from, `/`; a relative `cd garden` failed unless the model first did `cd /home/<user>`. The probe now passes the shell's real directory through.
- **Agent mode crashed instead of asking permission:** when the planner reached a command that needs confirmation (`python`, `rm`, `mv`, `forge`, ...) the `gemini` command raised `KeyError('success')` on the confirm effect. The effect is now handed to the front end and the confirmation dialog appears.
- **Literal `\n` in command output:** the same doubled-backslash paste bug in `find` (all results on one line), `jobs`, `story log`, `character journal`, the audit log (`/var/log/audit.log` was one line) and `backup`'s error text. Fixed; `find` now prints one path per line.
- **Agent mode never ran its plan:** the numbered-line regexes in `ai_manager.py` had doubled backslashes (`\\d`, `\\.`, `\\s` in raw strings), so no plan line ever matched and `gemini "<prompt>"` returned the plan as the answer. The same doubling put literal `\n` into every Ollama prompt and error message. All 58 undone.
- **JS `null` reached commands as `jsnull`, not `None`:** with no pipe, the bridge passes `null` for stdin and Pyodide delivers `pyodide.ffi.jsnull`, which is not `None`. Commands testing `stdin_data is not None` misbehaved; `wc` with no input crashed with `'JsNull' object has no attribute 'split'`. `kernel.execute_command` now normalises it once for every command. Pre-existing (same on the old Pyodide build), found by the new `python` command's tests.
- **Ghost Limb Fix:** Resolved `ModuleNotFoundError` for `bone_driver` by correctly registering it in the Kernel Manifest.
- **Amnesia Fix:** Patched `ai_manager.py` to inject `simulated_current_path` into the execution context, preventing the Autopilot from defaulting to `/` (Root) during multi-step plans.
- **Cache Exorcism:** Purged stale `gemini.py` definitions from the browser/Python cache.

---

## [0.0.5] - 2024-XX-XX
### Added
- Initial release of FractalOS (Hybrid Web/Python Architecture).
- Core Kernel (`kernel.py`, `filesystem.py`, `executor.py`).
- AI Manager with basic "Agentic Search" (Librarian Mode).
- Basic Tools: `ls`, `cat`, `grep`, `story`, `edit`.
