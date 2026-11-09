# Architecture

How FractalOS fits together, for a session that has never seen it. This is the map, not the territory: it names
the parts and the rules between them and leaves the detail to the code. Update it when the shape changes (a
module added, moved or merged, an interface or boundary changed), not for every change inside one.

Why things are this way lives in [DECISIONS.md](DECISIONS.md). The long-form tour for readers is the codex in
[manual/index.html](manual/index.html); where the two disagree, the code wins and this file is corrected.
Written 2026-11-08 (P10-04) from the code at `1ea2afd`, not from the manual.

## The shape, in one paragraph

The browser loads `resources/index.html`, which loads `scripts/asset_manifest.js` and then every script it lists,
in order, as classic scripts sharing one global scope (D-003). `main.js` builds the managers and calls
`FractalOS_Kernel.initialize` in `bridge.js`, which boots Pyodide (CPython 3.14 in WebAssembly), copies the Python
files named in `core/manifest.json` into Pyodide's file system and hands the kernel three callbacks: save the VFS,
read and write host files, run a host command. A typed line goes through `executePythonCommand` (`boot.js`) to
`kernel.execute_command` and the executor, which runs one Python module per command and returns output, an
error, or effects. The front end prints the result, performs each effect (`effect_handler.js`), and re-reads the
VFS from Python. Python owns the file system, users, groups and permissions; JavaScript owns the page, storage,
audio, the network and every browser API (D-001, D-002).

## Code map

| Area | Where | Entry point | Talks to |
| --- | --- | --- | --- |
| Boot and wiring | `resources/main.js`, `resources/scripts/asset_manifest.js` | `window.onload` | every manager; `FractalOS_Kernel` |
| JS to Python bridge | `resources/bridge.js` | `FractalOS_Kernel.initialize`, `.syscall()`, `.execute_command()` | Pyodide; `core/kernel.py` |
| Kernel dispatch | `resources/core/kernel.py` | `syscall_handler`, `execute_command`, `MODULE_DISPATCHER` | the core managers below |
| Command line | `resources/core/executor.py` | `CommandExecutor.execute` | `commands.<name>`; session; filesystem |
| Commands | `resources/core/commands/` | `run(args, flags, user_context, ...)` per module | the core managers; never the page |
| File system | `resources/core/filesystem.py` | `fs_manager` | the save callback; host file callbacks |
| Accounts | `resources/core/users.py`, `groups.py`, `sudo.py`, `session.py`, `audit.py` | `user_manager` and friends | filesystem (`/etc/...`) |
| Agent | `resources/core/ai_manager.py`, `bone_driver.py`, `swarm_manager.py` | `ai_manager` | `pyodide.http.pyfetch`; the executor |
| Snapshots | `resources/core/story_manager.py` | `story_manager` | filesystem (`.story/`) |
| App backends | `resources/core/apps/` | one manager per app | filesystem |
| Effects | `resources/scripts/effect_handler.js` | one `case` per effect name | the managers below |
| Front-end managers | `resources/scripts/*.js` | one class per concern (storage, fs mirror, users, output, terminal, sound, network, windows, panes, status bar, clipboard, hardware) | the DOM, browser APIs, the kernel |
| Apps | `resources/scripts/apps/` | `*_manager.js` + `*_ui.js` on `App` (`app.js`) | the kernel through `syscall` |
| Mesh relay | `extras/signaling_server.py` (`resources/dep/signaling_server.cjs` is the older Node one) | `main(bind, port)` | browsers over WebSocket |
| Installers | `extras/provision_x64.sh`, `extras/provision_appliance.sh` | the script | systemd, Chromium, `resources/deploy.json` |
| Public pages | `resources/landing.html`, `docs/manual/`, `docs/devlog.html` | static HTML | nothing at run time |

## Interfaces and data flow

```text
keystroke -> boot.js executePythonCommand -> createKernelContext (JSON snapshot of JS state)
  -> FractalOS_Kernel.execute_command -> kernel.execute_command -> CommandExecutor.execute
  -> commands.<name>.run -> {output | error | effect(s)}
  -> OutputManager prints, effect_handler.js performs effects, FileSystemManager re-reads the VFS
VFS write in Python -> save callback -> StorageHAL.save -> IndexedDB (browser) or data/fractalos_fs.json (Neutralino)
```

| Interface | Producer | Consumer | Contract |
| --- | --- | --- | --- |
| `syscall(module, function, args, kwargs)` | front-end managers and apps | `kernel.syscall_handler` | JSON in and out; `module` must be a key of `MODULE_DISPATCHER` (20 today), `function` any attribute of it |
| Kernel context | `createKernelContext` (`boot.js`) | `CommandExecutor` | JSON snapshot per line: current user and group, all users and groups, cwd, jobs, config flags, API key, session stack |
| Command result | each `commands/*.py` | the executor, then JS | `{"success": true, "output"}`, `{"success": false, "error": {"message", "suggestion"}}`, or `{"effect": ...}` / `{"effects": [...]}` |
| Effects | commands | `effect_handler.js` | 82 `case` labels on 2026-11-08 (some are sub-actions of `window_action`, `status_action`, `clipboard_action`, `multiplexer_action`); an unknown effect prints "Unknown effect from Python" and does nothing else |
| Kernel file list | `tools/gen_manifest.py` | `bridge.js` | `core/manifest.json`: `core`, `apps`, `commands` (152); generated, never hand-edited (D-010) |
| Script load list | hand-written | `index.html` | `asset_manifest.js`; order matters (D-003) |
| Mesh messages | `NetworkManager` | other tabs and nodes | BroadcastChannel `fractal-network` between tabs; WebSocket to the relay for signaling; WebRTC data channels between peers |
| Runtime mesh switch | the installer | `NetworkManager._applyDeployConfig` | optional `resources/deploy.json`: `networking`, `signalingUrl` (`"auto"` = page host), `signalingPort` (D-046) |
| LLM providers | `ai_manager.py` | Gemini, Ollama, llama.cpp | Gemini `generateContent` with an `x-goog-api-key` header; Ollama `localhost:11434`; llama.cpp `localhost:8080/v1/chat/completions` |

## Invariants

- **Python decides; JavaScript mirrors.** File system, users, groups and permissions are decided in the kernel
  (D-001). Enforced by: convention and review only.
- **Commands never touch the page.** Anything visible, audible or browser-specific is an effect (D-002). On
  2026-11-08 no module under `core/commands/` imports `js`; `ai_manager.py` imports `js.AbortSignal` for fetch
  timeouts. Enforced by: nothing automated.
- **Every kernel file is in `core/manifest.json` and every script and stylesheet is in `asset_manifest.js`.**
  Enforced by: `tests/structure.js` (D-010).
- **One command path.** Typed lines, scripts, apps and the agent all go through `CommandExecutor`, so the
  agent meets the same permissions and audit log as a user (roadmap principle 4). Enforced by:
  `tests/agent_unit.py` for the agent's own checks; no test proves no other path exists.
- **Effects apply after the whole line.** `cd x && cmd` runs `cmd` in the old directory (AGENTS.md). Enforced
  by: the executor's design; documented, not tested.
- **A JS value crossing raw into Python is normalised.** `jsnull` is not `None`; `kernel.execute_command`
  passes stdin through `_from_js` (D-012). Enforced by: a smoke-test check.
- **User text from apps reaches commands as JSON on stdin, never on the command line** (D-019). Enforced by:
  convention.
- **Installed packages are verified before they run.** The executor recomputes a package's SHA-256 against
  `/etc/pkg_manifest.json` on every load (D-044). Enforced by: `tests/pkg_security_test.py`.
- **The docs agree with each other.** Enforced by: `tools/check_docs.py`, run by `tests/structure.js` (P10-02).

## Boundaries

Where outside data comes in. Security consequences are in [SECURITY.md](SECURITY.md).

| Boundary | Comes in as | Checked by | Rule |
| --- | --- | --- | --- |
| Typed command line | text | executor parser; command flag definitions | runs as the current FractalOS user, under VFS permissions |
| LLM reply | JSON or text from `pyfetch` | plan parsing and validation, `COMMAND_WHITELIST`, voltage (`bone_driver.py`) | a plan is validated before any step runs; risky steps need confirmation, a snapshot or `--force` |
| Mesh peer | WebSocket and WebRTC messages | `NetworkManager` handlers; swarm policy `/etc/swarm.conf` (D-036) | remote agent work runs under the receiving node's voltage budget and policy |
| Package file | `.fpkg` archive or repository index | checksum at install and at load; `pkg audit` static scan (D-044) | elevated scopes need `--trust` or `--force` |
| Host files (Portable) | a folder the user picks in a native dialog | `mount host` effect | only the picked folder is mounted |
| Host commands (Portable) | a string to `Neutralino.os.execCommand` | each caller; only `gpio` (through `host_api`) and `HardwareManager` build one today, and both accept only a numeric pin (P6-05) | never build a host command from text that is not checked against a fixed form |
| Dropped or pasted files | browser `File` / clipboard | `ClipboardManager` (D-040) | written into the VFS as the current user |

## Dependencies

All vendored under `resources/dep/`; nothing is fetched from a CDN at run time. A new one needs the owner's
approval and, for Python, a wheel plus a `pyodide-lock.json` entry (D-004).

| Dependency | Version | For | Why |
| --- | --- | --- | --- |
| Pyodide | 314.0.7 (CPython 3.14.2, lock `abi 2026_0`) | the kernel | D-004; trimmed to the core files and four wheels |
| `cryptography` (+ `cffi`, `pycparser`, `six`) | 47.0.0 (2.0.0, 3.0, 1.17.0) | PBKDF2 password hashing | D-007 |
| marked | 16.0.0 | Markdown rendering in the editor, Chidi and Samwise chat apps | |
| DOMPurify | 3.0.8 | sanitising that rendered HTML | |
| html2canvas | 1.4.1 | screenshots (`capture_screenshot_png`) | |
| Tone.js | not recorded in the file | sounds | |
| `websockets` (host Python) | whatever the host has; 13+ supported | `extras/signaling_server.py` | P9-03 |
| Neutralinojs | config pins 6.2.0 | Portable mode | P5-02 |

## State and caches

| What | Where | Written by | Reset by | Committed? |
| --- | --- | --- | --- | --- |
| The VFS (one JSON tree) | IndexedDB `FractalOS` v5, store `FileSystemsStore`, key `FractalOS_SharedFS`; Portable: `data/fractalos_fs.json` | the save callback on every write | the `full_reset` effect; clearing site data | no (`data/` gitignored) |
| Session keys (credentials, aliases, onboarding flag, terminal state, Gemini key, groups) | localStorage `FractalOS*` keys (`config.js` `STORAGE_KEYS`); Portable: `data/fractalos_localstorage.json` | `StorageManager` | `full_reset`; clearing site data | no |
| Snapshots | `.story/` inside the VFS | `story` | `story` itself | inside the VFS only |
| Mesh switch | `resources/deploy.json` | the installers | `--uninstall` or by hand | no (gitignored) |
| Agent transcripts | `tests/out/` | `tests/agent.js` | by hand | no (gitignored) |
| Release bundles | `dist/` | `tools/package_release.py` | by hand | no (gitignored) |

## Failure modes and observability

| Failure | User-visible behaviour | Detection | Recovery |
| --- | --- | --- | --- |
| A Python file missing from `core/manifest.json` | "command not found" or `ModuleNotFoundError` | `tests/structure.js` | `python3 tools/gen_manifest.py` |
| A script missing from `asset_manifest.js` | a feature silently absent | `tests/structure.js` | add it in load order |
| Pyodide fails to load (served from `file://`, missing wasm) | the kernel never becomes ready | `FractalOS_Kernel.isReady` stays false; smoke test | serve over http |
| LLM provider down or key missing | `samwise` reports the error; nothing runs | the command's error result | start Ollama or set the key |
| Relay unreachable | no remote peers; tabs still meet over BroadcastChannel | `peers`, `netstat --mesh` | start `extras/signaling_server.py` |
| A tampered package | refused at load with `SecurityError` | `pkg verify` | reinstall |
| Storage full or blocked | writes stop persisting | console errors from `StorageHAL` | free space; export first |

What may be logged: the audit log (`/var/log/audit.log`) records commands and agent actions. Nothing should log
the Gemini key or password hashes; nothing checks that.

## Claims vs. code

- **The manual and landing page count 150 or 151 commands; `core/manifest.json` lists 152** (2026-11-08).
- **llama.cpp and the signaling relay both default to port 8080.** On a box running the relay, the `llamacpp`
  provider would talk to the relay. Not observed; read from `ai_manager.py` and `signaling_server.py`.
- **"Network-free" pages and an "offline-first" mesh, but WebRTC uses `stun:stun.l.google.com:19302`** for ICE
  (`network_manager.js`). A mesh that only spans a LAN may not need it; nobody has tried without.
- **The landing page calls the mesh "unhackable"; the relay and web server are unauthenticated** (P9-06).
