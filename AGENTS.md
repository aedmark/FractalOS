# FractalOS

A browser-based, Unix-flavoured virtual operating system with a Python kernel that runs inside the page under
Pyodide (WebAssembly) and a JavaScript front end that draws the terminal, plays sounds and hosts the apps. It
runs as a static site over any web server, or as a desktop app under Neutralinojs. An LLM (`samwise` command:
Gemini API or a local Ollama) sits inside the shell as a user-facing agent. No build step, no npm dependencies.

## Session protocol

Sessions are short-lived and context resets between them, so the repo carries the memory.

**Start of every session**
1. Read `docs/HANDOFF.md`: "Current state" and the latest session-log entry.
2. Read `docs/ROADMAP.md` for the item(s) you are about to work on. Skim `docs/DECISIONS.md` before making a design
   choice, and `docs/TESTING.md` before claiming anything works.
3. Confirm the plan with the user in one or two lines, then work on roadmap items by ID.

**While working**
- Work one roadmap item at a time; keep each commit scoped to it. Reference IDs (`P1-04`) in commit messages.
- If you make a choice a future session might question, add an entry to `docs/DECISIONS.md`.
- If you discover new work, append a new item to `docs/ROADMAP.md` (never renumber existing IDs).
- Run `node tests/structure.js` after adding or moving any file, the smoke test before declaring anything done,
  and the diag suite after touching Python (see "Running and testing").

**End of every session (or when the user says to wrap up)**
1. Tick / update items in `docs/ROADMAP.md`.
2. Rewrite the **Current state** and **Next steps** sections of `docs/HANDOFF.md` so they are true right now.
3. Add a session-log entry at the top of the log using the template in HANDOFF.md.
4. Never leave "Current state" describing something that is no longer true. Handoff docs that lie are worse than none.

## Layout

| Path | Purpose |
| --- | --- |
| `resources/index.html` | The page. Loads `scripts/asset_manifest.js`, then every CSS and JS file it lists, in order |
| `resources/scripts/asset_manifest.js` | The ordered load list. A new script file must be added here or it never loads |
| `resources/main.js` | `window.onload`: builds every manager, wires dependencies, boots the kernel, runs onboarding or restores the session |
| `resources/bridge.js` | `FractalOS_Kernel`: loads Pyodide, copies the files named in `core/manifest.json` into the Pyodide FS, exposes `syscall()` and `execute_command()` |
| `resources/core/manifest.json`, `tools/gen_manifest.py` | Generated list of every kernel Python file. Regenerate after adding, renaming or deleting one (D-010) |
| `resources/scripts/boot.js` | `executePythonCommand` (the one path a shell command takes), `createKernelContext`, terminal key handling |
| `resources/scripts/effect_handler.js` | The front-end half of the effect contract (D-002): one `case` per effect name |
| `resources/scripts/*.js` | One manager per concern: storage, fs, users, groups, sudo, session, output, terminal UI, modals, sound, network, theme |
| `resources/scripts/apps/` | Front-end apps (editor, paint, adventure, chidi, samwise_chat, log, top, basic, onboarding), each `*_ui.js` + `*_manager.js`, on the `App` base class in `app.js` |
| `resources/core/kernel.py` | `syscall_handler` and `MODULE_DISPATCHER`: the single entry point from JS into Python |
| `resources/core/executor.py` | Parses a command line (pipes, `&&`, `\|\|`, redirection, `&`, brace expansion, substitution), runs commands, collects effects |
| `resources/core/filesystem.py` | The virtual file system: one JSON tree, permissions, symlinks, and the save callback back to JS |
| `resources/core/users.py`, `groups.py`, `sudo.py`, `session.py`, `audit.py` | Accounts (PBKDF2 via `cryptography`, D-007), groups, sudoers, env/history/alias/session stack, audit log |
| `resources/core/ai_manager.py`, `bone_driver.py` | LLM calls (`pyodide.http.pyfetch`), the planner / synthesizer / chat / remix / forge prompts, and the BoneAmanita autopilot persona and "voltage" audit |
| `resources/core/story_manager.py` | `story`: snapshot-based versioning inside the VFS (`.story/`) |
| `resources/core/commands/*.py` | One module per shell command (124 of them). Interface: `run`, optional `define_flags`, `man`, `help` |
| `resources/core/apps/*.py` | Kernel-side state for the apps (editor undo stack, paint, adventure, top, log, basic) |
| `resources/dep/` | Vendored third-party code: `pyodide/` (trimmed, D-004), Tone.js, marked, DOMPurify, html2canvas |
| `resources/start_server.sh`, `stop_server.sh` | `python3 -m http.server 8000` from `resources/` |
| `neutralino.config.json`, `resources/neutralino.js`, `www/` | Desktop (Portable) mode. `www/` is the untouched Neutralino template, not the app |
| `extras/diag.sh`, `extras/inflate.sh` | In-OS shell scripts: a 1,400-line command test suite and a demo-world generator (see `docs/TESTING.md`) |
| `tests/structure.js` | Node-only, instant: the manifest and `asset_manifest.js` match the files on disk (D-010) |
| `tests/smoke.js`, `tests/diag.js` | Headless-Chromium tests (Node + Playwright): a kernel smoke test, and a runner that executes `extras/diag.sh` inside the OS and grades it |
| `tests/agent.js`, `tests/fake_ollama.py` | Headless run of the `samwise` agent (autopilot and agent mode) through seven tasks against a real Ollama, graded on the file system, transcript to `tests/out/`; and a stand-in Ollama that proves the plumbing without a model (D-014) |
| `tests/agent_grading.js`, `tests/agent_unit.py` | No browser, no model: the agent harness's graders against canned outcomes, and unit tests of plan parsing and validation, stop-on-failure, voltage and `--force`, checkpoints and `forge` escapes |
| `tests/test_executor.py` | Runs **inside FractalOS** (`python test_executor.py` after copying it into the VFS) to exercise the `python` command; it imports the kernel, so plain `python3` on the host cannot run it |
| `docs/ROADMAP.md` | The plan, with stable item IDs |
| `docs/HANDOFF.md` | Current state, next steps, session log |
| `docs/DECISIONS.md` | Append-only decision record |
| `docs/TESTING.md` | How to run and read the tests, and the pitfalls already hit |
| `README.md`, `docs/CONTRIBUTING.md`, `docs/CHANGELOG.md` | Public-facing docs. Keep them consistent with the files above; they do not replace them |

## How a command runs

1. Enter in the terminal (`boot.js`) → `executePythonCommand(text)` → `createKernelContext()` builds a JSON
   snapshot of the JS-side state (current user and group, all users and groups, cwd, jobs, config flags, API key,
   session stack) and syncs aliases and history into Python.
2. `FractalOS_Kernel.execute_command(text, contextJson)` → `kernel.execute_command` → `command_executor.execute`.
   The executor loads that context, parses the line, imports `commands.<name>` and calls its `run(...)`.
3. The command returns `{"success": true, "output": ...}`, `{"success": false, "error": {"message", "suggestion"}}`,
   or an **effect** (`{"effect": "play_sound", ...}`) for anything the kernel cannot do itself (D-002).
4. JS prints output or errors, runs each effect through `effect_handler.js`, then re-reads the whole VFS from
   Python (`FileSystemManager.getFsData`) so the JS copy matches. Writes in Python also call back into
   `StorageHAL.save` so the tree is persisted.

Python is the source of truth for the file system, users, groups and permissions. JS keeps a mirror for the UI
and owns localStorage, IndexedDB, the DOM, audio and the browser APIs.

## Conventions

- Vanilla JS, classic `<script>` files sharing one global scope, loaded in `asset_manifest.js` order (D-003).
  Not ES modules. Top-level `const` objects (`FractalOS_Kernel`, `CommandExecutor`, `dependencies`) are globals
  but are **not** `window` properties; tests reach them by bare name.
- Python: PEP 8, standard library plus `cryptography` only. Anything else means adding a wheel to
  `resources/dep/pyodide/` **and** to `pyodide-lock.json` (D-004). Ask first.
- A new Python file anywhere under `resources/core/` (a command, an app backend, a core module) needs
  `python3 tools/gen_manifest.py` run afterwards, or `bridge.js` never copies it into Pyodide and "command not
  found" (or the CHANGELOG's "ghost limb" `ModuleNotFoundError`) is the only symptom. `node tests/structure.js`
  catches the omission (D-010). Never edit `core/manifest.json` by hand.
- Commands must never touch the DOM or JS. Return an effect and add a `case` in `effect_handler.js`.
- Effects apply after the whole line: `cd x && cmd` runs `cmd` in the old directory. Separate lines.
- A JS value handed straight to Python (not as JSON) may be `pyodide.ffi.jsnull`, which is not `None`.
  `kernel.execute_command` normalises stdin with `_from_js`; do the same for any new raw crossing (D-012).
- The `MESSAGES` in `config.js` are in the OS's own voice (wry, in character). Match it in new user-facing text.

## Running and testing

- **Browser mode:** serve `resources/` over http (`resources/start_server.sh`, or `python3 -m http.server 8000`
  from `resources/`) and open `http://localhost:8000/`. It does not work from `file://` (Pyodide fetches its
  wasm and the kernel copies `core/*.py` with `fetch`).
- **Portable mode:** put the Neutralinojs binary in the repo root and run it (`neutralino.config.json` points
  `documentRoot` at `/resources/`). Data lands in `data/` next to the binary.
- **Structure test:** `node tests/structure.js`. No browser or server; a second. Fails if a Python file is not
  in `core/manifest.json` (fix: `python3 tools/gen_manifest.py`) or a script or stylesheet is not in
  `asset_manifest.js`.
- **Smoke test:** `node tests/smoke.js http://127.0.0.1:8000/index.html` with a server running. Needs Node 18+
  and Playwright with a Chromium (`npm i -g playwright` or `npx playwright install chromium`). Boots the page,
  waits for the kernel, runs first-time user setup and a handful of shell commands, exits non-zero on any
  failure. Details and known traps: `docs/TESTING.md`.
- **In-OS suite:** `node tests/diag.js http://127.0.0.1:8000/index.html` runs `extras/diag.sh` (a FractalOS shell
  script, not bash) inside the OS as root and grades its `check_fail` assertions and error lines. About two
  minutes. Run it after any change to the kernel, the executor or a command.
- **Agent harness:** `AGENT_MODEL=<ollama model> node tests/agent.js http://127.0.0.1:8000/index.html` with Ollama
  on `localhost:11434` (or `python3 tests/fake_ollama.py &` for a plumbing-only run). Seven tasks, PASS/FAIL on
  file-system facts; transcript in `tests/out/agent-transcript.md`. Needs a machine with a model. Local
  recipe (Playwright in a scratch directory, system Chromium) in `docs/TESTING.md`.
- **Grader and agent unit tests:** `node tests/agent_grading.js` and `python3 tests/agent_unit.py`. Seconds, no
  browser or model. Run them after touching `tests/agent.js`, `ai_manager.py` or `bone_driver.py`.
- Nothing here runs under `npm test`; there is no `package.json`.
