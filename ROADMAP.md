# FractalOS Roadmap

A browser-based virtual operating system: a Python kernel under Pyodide, a JavaScript terminal and app layer,
and an LLM inside the shell. Runs as a static site or as a Neutralinojs desktop app.

This file is the **plan**. For *where we are right now* read [docs/HANDOFF.md](docs/HANDOFF.md). For *why we chose
things* read [docs/DECISIONS.md](docs/DECISIONS.md). For *how to check it* read [docs/TESTING.md](docs/TESTING.md).

## Principles

These break ties when a feature is debatable.

1. **Python is the source of truth.** File system, users, groups, permissions and command logic live in the
   kernel. JS mirrors state for the UI; it does not decide it.
2. **The kernel never touches the page.** Anything visible, audible or browser-specific is an effect the kernel
   returns and the front end performs (D-002).
3. **No build step, no install.** Clone, serve `resources/`, open a browser. Vendored dependencies stay small
   enough that the repo clones in seconds (D-004, D-005).
4. **The AI is a user, not root.** Whatever the `gemini` agent runs goes through the same executor, whitelist,
   permissions and audit log as a typed command, and a risky plan needs a snapshot or a `--force`.
5. **Verified means observed.** A feature is done when the smoke test or the in-OS suite has seen it work, not
   when the code reads right.

## Status legend

`[ ]` not started · `[~]` in progress · `[x]` done · `[-]` dropped (say why in DECISIONS.md)

Every item has a stable ID (`P1-03`). Reference IDs in commits and in HANDOFF.md. Never renumber; append new items.

---

## Phase 0: What exists (done before this record began)

Built between 2025-11-23 and 2026-01-01 by the owner, before the docs in this repo existed. Recorded here so the
IDs exist; the code is the evidence, not a test run.

- [x] P0-01 Python kernel under Pyodide with a single `syscall_handler` and a JS bridge (`bridge.js`, `kernel.py`)
- [x] P0-02 Virtual file system with owners, groups, modes, symlinks, `fsck`, size limits, persisted to IndexedDB
  (browser) or `data/` (Neutralino)
- [x] P0-03 Users, groups, PBKDF2 passwords, `sudo` with a virtual `/etc/sudoers` and `visudo`, audit log
- [x] P0-04 A shell: pipes, `&&` / `||`, redirection, background jobs, brace expansion, command substitution,
  aliases, env vars, history with Ctrl+R search, tab completion, `run` for scripts
- [x] P0-05 123 commands (`ls`, `grep`, `sed`, `awk`, `zip`, `diff`, `patch`, `bc`, `nc`, `binder`, `agenda`, ...)
- [x] P0-06 Apps on the `App` base class: editor, paint, text adventure (with a creator), Chidi document
  assistant, Gemini chat, log, top, BASIC interpreter, onboarding
- [x] P0-07 `gemini` command: planner → whitelisted commands → synthesizer loop, chat mode, `remix`, `forge`,
  `storyboard`, `planner`, `chidi`; providers Gemini (API key in localStorage) and Ollama (localhost)
- [x] P0-08 `story`: snapshot versioning inside the VFS
- [x] P0-09 Cinematic mode, themes, Tone.js sounds, `printscreen`, pager, BroadcastChannel "networking" (`nc`,
  `netstat`, `post_message`), disabled by default
- [x] P0-10 Neutralinojs portable mode with a storage HAL that swaps IndexedDB for real files
- [x] P0-11 BoneAmanita autopilot: `gemini --autopilot` / `--force`, `bone_driver.py` persona and voltage audit,
  `forge` command (CHANGELOG "Unreleased")

## Phase 1: Foundations and hygiene

Goal: a repo a new session can clone fast, read in ten minutes, and verify in one command.

- [x] P1-01 Roadmap, handoff, decisions and testing docs, and the `CLAUDE.md` session protocol (2026-09-24)
- [x] P1-02 Trim the vendored Pyodide to the core runtime plus the wheels the kernel loads, and upgrade it
  (0.28.0.dev0 → 314.0.7, Python 3.14) (D-004)
- [x] P1-03 Rewrite git history once to drop the 415 MB of old Pyodide blobs (pack 327 MB → 9 MB) (D-005)
- [x] P1-04 Headless smoke test (`tests/smoke.js`): boot, first-time setup, password verify, shell commands (D-008)
- [x] P1-05 `.gitignore` (`data/`, `.tmp/`, logs, `.idea/`, `node_modules/`)
- [ ] P1-06 Run `extras/diag.sh` headlessly through the smoke harness and make its result the pass/fail gate; count
  its `check_fail` assertions and fix what it finds
- [ ] P1-07 Untrack `.idea/` and `neutralinojs.log` (they are committed today; `.gitignore` alone does not remove
  them). Owner's call, since `.idea/` is their PyCharm project.
- [ ] P1-08 Generate the `commandFiles` / `coreFiles` lists in `bridge.js` from the directory (a script, or a
  manifest file the kernel reads) so a new command cannot be forgotten; a test that fails when the lists and
  `resources/core/` disagree
- [ ] P1-09 Reconcile README claims with the code: `python` command is "planned" in the README and appears in the
  AI whitelist and voltage table but there is no `commands/python.py`; "Package Management (Coming Soon)" has
  only `loadPackageManifest` reading `/etc/pkg_manifest.json`. Decide: build or delete the claims.
- [ ] P1-10 Delete or explain `www/` (the stock Neutralino "It works" template; `documentRoot` is `/resources/`)
- [ ] P1-11 Automated check that every module in `resources/core/commands/` exposes `run` and `man`, and that
  `help` lists it

## Phase 2: The agent

Goal: the `gemini` loop and the BoneAmanita autopilot are trustworthy enough to leave running.

- [ ] P2-01 Verify the autopilot end to end against a local Ollama: plan, voltage report, `--force`, `story save`
  interlock, multi-step `cd` memory ("stateless memory injection"). Nothing in this phase has been observed by a
  session yet; the CHANGELOG entries are the owner's.
- [ ] P2-02 Voltage calibration with evidence: a table of plans and their scores, and the thresholds justified
- [ ] P2-03 Decide the fate of `python` in the AI whitelist and `bone_driver.py` (see P1-09); the persona prompt
  currently tells the model the system cannot run Python, which is true
- [ ] P2-04 Chidi and `remix` / `storyboard` verified against Gemini and Ollama with a recorded transcript
- [ ] P2-05 Gemini model and endpoint are hard-coded (`gemini-1.5-flash`, `v1beta`); make the model configurable
  through `/etc/ai.conf` for Gemini as it already is for Ollama, and pick a current default
- [ ] P2-06 Timeouts and errors from `pyfetch` surface to the user in the OS voice, with the provider named

## Phase 3: Milestone 1, the AI Town Manager (the README's stated direction)

Goal: give the agent long-term memory and the ability to carry out multi-step tasks on its own. Not designed
yet; these are placeholders for the owner to shape.

- [ ] P3-01 Design: where memory lives (VFS files? `story` snapshots? a kernel module?) and what the agent may
  read back. Write it up as a decision before code.
- [ ] P3-02 Multi-step task execution with a visible plan, per-step confirmation or a voltage budget, and a
  transcript in the audit log
- [ ] P3-03 A way for the user to interrupt a running plan (`kill` on the agent's job)

## Phase 4: Packages and extensibility

- [ ] P4-01 Package management: define what a package is (a command file? an app? a Pyodide wheel?), how it is
  installed into the VFS, and how `/etc/pkg_manifest.json` feeds `help` and tab completion
- [ ] P4-02 Loading extra Pyodide wheels at runtime from `resources/dep/pyodide/` for packages that need them,
  with the lock file kept honest (D-004)

## Phase 5: Networking and portable mode (open questions)

Not committed. The BroadcastChannel layer works between tabs; the WebSocket signaling path expects a server at
`ws://localhost:8080` that is not in this repo.

- [ ] P5-01 Decide whether the signaling server is in scope; if so add it, if not remove the WebSocket path
- [ ] P5-02 Portable mode verified on Linux, macOS and Windows with a recorded Neutralino version (the config
  pins 6.2.0; `neutralinojs.log` in the repo is from 2025-08-22)
- [ ] P5-03 Real-disk access from the VFS in portable mode beyond `data/` (mount a host folder)

## Known limitations (deliberate, revisit)

- `Guest` cannot write outside `/home/Guest`; the smoke test's `mkdir /home/t` failing is correct behaviour.
- The `ssl` module under Pyodide 314 is a stub (`ssl.OPENSSL_VERSION` reports "OpenSSL (stub)"); `pyfetch` uses
  the browser's fetch, so HTTPS still works. Nothing in the kernel should import `ssl` for real TLS.
- `hashlib` under Pyodide 314 has the built-in algorithms only; `story` uses `sha1`, which is fine.
- The VFS is one JSON tree saved whole on every write. Fine at the sizes it is used at; `MAX_VFS_SIZE` is 640 MB
  in config but nothing that large has been tried.
