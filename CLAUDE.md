# FractalOS

A browser-based, Unix-flavoured virtual operating system with a Python kernel that runs inside the page under
Pyodide (WebAssembly) and a JavaScript front end that draws the terminal, plays sounds and hosts the apps. It
runs as a static site over any web server, or as a desktop app under Neutralinojs. An LLM (`gemini` command:
Gemini API or a local Ollama) sits inside the shell as a user-facing agent. No build step, no npm dependencies.

The code still calls itself **OopisOS** in many places (`OopisOS_Kernel`, the `oopisOs*` localStorage keys, the
`oopisos-network` BroadcastChannel, "OopisOS Python Kernel is online"). FractalOS is the product name; OopisOS is
the internal one and is not being renamed (D-009).

## Session protocol

Sessions are short-lived and context resets between them, so the repo carries the memory.

**Start of every session**
1. Read `docs/HANDOFF.md`: "Current state" and the latest session-log entry.
2. Read `ROADMAP.md` for the item(s) you are about to work on. Skim `docs/DECISIONS.md` before making a design
   choice, and `docs/TESTING.md` before claiming anything works.
3. Confirm the plan with the user in one or two lines, then work on roadmap items by ID.

**While working**
- Work one roadmap item at a time; keep each commit scoped to it. Reference IDs (`P1-04`) in commit messages.
- If you make a choice a future session might question, add an entry to `docs/DECISIONS.md`.
- If you discover new work, append a new item to `ROADMAP.md` (never renumber existing IDs).
- Run the smoke test before declaring anything done (see "Running and testing").

**End of every session (or when the user says to wrap up)**
1. Tick / update items in `ROADMAP.md`.
2. Rewrite the **Current state** and **Next steps** sections of `docs/HANDOFF.md` so they are true right now.
3. Add a session-log entry at the top of the log using the template in HANDOFF.md.
4. Never leave "Current state" describing something that is no longer true. Handoff docs that lie are worse than none.

## Layout

| Path | Purpose |
| --- | --- |
| `resources/index.html` | The page. Loads `scripts/asset_manifest.js`, then every CSS and JS file it lists, in order |
| `resources/scripts/asset_manifest.js` | The ordered load list. A new script file must be added here or it never loads |
| `resources/main.js` | `window.onload`: builds every manager, wires dependencies, boots the kernel, runs onboarding or restores the session |
| `resources/bridge.js` | `OopisOS_Kernel`: loads Pyodide, copies `core/` into the Pyodide FS, exposes `syscall()` and `execute_command()`. Holds the kernel file manifest (D-003) |
| `resources/scripts/boot.js` | `executePythonCommand` (the one path a shell command takes), `createKernelContext`, terminal key handling |
| `resources/scripts/effect_handler.js` | The front-end half of the effect contract (D-002): one `case` per effect name |
| `resources/scripts/*.js` | One manager per concern: storage, fs, users, groups, sudo, session, output, terminal UI, modals, sound, network, theme |
| `resources/scripts/apps/` | Front-end apps (editor, paint, adventure, chidi, gemini_chat, log, top, basic, onboarding), each `*_ui.js` + `*_manager.js`, on the `App` base class in `app.js` |
| `resources/core/kernel.py` | `syscall_handler` and `MODULE_DISPATCHER`: the single entry point from JS into Python |
| `resources/core/executor.py` | Parses a command line (pipes, `&&`, `\|\|`, redirection, `&`, brace expansion, substitution), runs commands, collects effects |
| `resources/core/filesystem.py` | The virtual file system: one JSON tree, permissions, symlinks, and the save callback back to JS |
| `resources/core/users.py`, `groups.py`, `sudo.py`, `session.py`, `audit.py` | Accounts (PBKDF2 via `cryptography`, D-007), groups, sudoers, env/history/alias/session stack, audit log |
| `resources/core/ai_manager.py`, `bone_driver.py` | LLM calls (`pyodide.http.pyfetch`), the planner / synthesizer / chat / remix / forge prompts, and the BoneAmanita autopilot persona and "voltage" audit |
| `resources/core/story_manager.py` | `story`: snapshot-based versioning inside the VFS (`.story/`) |
| `resources/core/commands/*.py` | One module per shell command (123 of them). Interface: `run`, optional `define_flags`, `man`, `help` |
| `resources/core/apps/*.py` | Kernel-side state for the apps (editor undo stack, paint, adventure, top, log, basic) |
| `resources/dep/` | Vendored third-party code: `pyodide/` (trimmed, D-004), Tone.js, marked, DOMPurify, html2canvas |
| `resources/start_server.sh`, `stop_server.sh` | `python3 -m http.server 8000` from `resources/` |
| `neutralino.config.json`, `resources/neutralino.js`, `www/` | Desktop (Portable) mode. `www/` is the untouched Neutralino template, not the app |
| `extras/diag.sh`, `extras/inflate.sh` | In-OS shell scripts: a 1,400-line command test suite and a demo-world generator (see `docs/TESTING.md`) |
| `tests/smoke.js` | Headless-Chromium boot and kernel smoke test (Node + Playwright) |
| `ROADMAP.md` | The plan, with stable item IDs |
| `docs/HANDOFF.md` | Current state, next steps, session log |
| `docs/DECISIONS.md` | Append-only decision record |
| `docs/TESTING.md` | How to run and read the tests, and the pitfalls already hit |
| `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md` | Public-facing docs. Keep them consistent with the files above; they do not replace them |

## How a command runs

1. Enter in the terminal (`boot.js`) → `executePythonCommand(text)` → `createKernelContext()` builds a JSON
   snapshot of the JS-side state (current user and group, all users and groups, cwd, jobs, config flags, API key,
   session stack) and syncs aliases and history into Python.
2. `OopisOS_Kernel.execute_command(text, contextJson)` → `kernel.execute_command` → `command_executor.execute`.
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
  Not ES modules. Top-level `const` objects (`OopisOS_Kernel`, `CommandExecutor`, `dependencies`) are globals
  but are **not** `window` properties; tests reach them by bare name.
- Python: PEP 8, standard library plus `cryptography` only. Anything else means adding a wheel to
  `resources/dep/pyodide/` **and** to `pyodide-lock.json` (D-004). Ask first.
- A new command is a new file in `resources/core/commands/` **plus** a line in the `commandFiles` list in
  `bridge.js`; without the second it is never copied into Pyodide and "command not found" is the only symptom.
- A new Python core module likewise goes in `coreFiles` in `bridge.js` (that is the "ghost limb" bug in the
  CHANGELOG).
- Commands must never touch the DOM or JS. Return an effect and add a `case` in `effect_handler.js`.
- Keep the `oopisOs*` localStorage keys and the `FractalOS` / `FileSystemsStore` IndexedDB names (D-006).
- The `MESSAGES` in `config.js` are in the OS's own voice (wry, in character). Match it in new user-facing text.

## Running and testing

- **Browser mode:** serve `resources/` over http (`resources/start_server.sh`, or `python3 -m http.server 8000`
  from `resources/`) and open `http://localhost:8000/`. It does not work from `file://` (Pyodide fetches its
  wasm and the kernel copies `core/*.py` with `fetch`).
- **Portable mode:** put the Neutralinojs binary in the repo root and run it (`neutralino.config.json` points
  `documentRoot` at `/resources/`). Data lands in `data/` next to the binary.
- **Smoke test:** `node tests/smoke.js http://127.0.0.1:8000/index.html` with a server running. Needs Node 18+
  and Playwright with a Chromium (`npm i -g playwright` or `npx playwright install chromium`). Boots the page,
  waits for the kernel, runs first-time user setup and a handful of shell commands, exits non-zero on any
  failure. Details and known traps: `docs/TESTING.md`.
- **In-OS suite:** `extras/diag.sh` is a FractalOS shell script (not bash). Upload it (`upload`) and `run` it
  inside the OS; it uses `check_fail` to assert failures. It has not been run headlessly yet (P1-06).
- Nothing here runs under `npm test`; there is no `package.json`.
