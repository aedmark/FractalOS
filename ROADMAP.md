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
- [x] P1-06 Run `extras/diag.sh` headlessly (`tests/diag.js`) and make its result the pass/fail gate. First run on
  Pyodide 314 / Python 3.14: 40 `check_fail` assertions pass, 0 fail, no command errors, script reaches its
  completion banner in about 100 s. Nothing needed fixing (2026-09-24)
- [~] P1-07 Untrack `.idea/` and `neutralinojs.log` (they are committed today; `.gitignore` alone does not remove
  them). Owner's call, since `.idea/` is their PyCharm project. *2026-09-25:* the owner deleted `.idea/` on
  `main`; `neutralinojs.log` is still tracked.
- [x] P1-08 `tools/gen_manifest.py` writes `resources/core/manifest.json` from the directories; `bridge.js`
  fetches it instead of carrying hand-typed lists; `tests/structure.js` fails when the manifest or
  `asset_manifest.js` drifts from disk (mutation-checked both ways) (D-010, 2026-09-24)
- [x] P1-09 Reconcile README claims with the code. Decided 2026-09-24: **build `python`** (the owner: "running real
  python inside FractalOS is definitely something that could be very useful"). Done as `commands/python.py`
  (D-011), README updated. The other stale claim, "Package Management (Coming Soon)" with only
  `loadPackageManifest` behind it, is P4-01's to settle.
- [ ] P1-10 Delete or explain `www/` (the stock Neutralino "It works" template; `documentRoot` is `/resources/`)
- [ ] P1-11 Automated check that every module in `resources/core/commands/` exposes `run` and `man`, and that
  `help` lists it
- [ ] P1-12 Audit the other raw JS→Python crossings for `jsnull` (D-012): `kernel.write_file` /
  `create_directory` / `top_get_process_list` take JS values directly (`to_py` handles objects, not `null`),
  and `syscall_handler` args arrive via JSON (safe). A grep for `is not None` / `is None` on bridge-fed values.

## Phase 2: The agent

Goal: the `gemini` loop and the BoneAmanita autopilot are trustworthy enough to leave running.

- [x] P2-01 Verified end to end against local Ollama after repairs: gemma4:12b **7/7** and llama3.1:8b
  **7/7** (2026-09-25, session 10). Both created files, honored cd, ran Python with output 55, answered a
  read-only question, confirmed and performed mv, braked deletion, and deleted with --force. Home checkpoint
  contents verified separately by smoke. Transcripts and scoped limitations in HANDOFF; P2-08 remains open.
- [x] P2-02 Operation-based voltage and calibration table in D-016; all delete spellings score 20,
  plain forge scores 5, argument text cannot alter risk. Autopilot writes require a real home checkpoint;
  missing story-save text no longer blocks creation (2026-09-25).
- [x] P2-03 The agent has `python`: whitelisted, confirmed-first in agent mode, `--steps` refused, persona
  rewritten. On the way, agent mode's plan regex was found never to have matched (doubled backslashes across
  `ai_manager.py`) and fixed, so default `gemini` mode executes plans for the first time (D-013, 2026-09-25)
- [ ] P2-04 Chidi and `remix` / `storyboard` verified against Gemini and Ollama with a recorded transcript
- [ ] P2-05 Gemini model and endpoint are hard-coded (`gemini-1.5-flash`, `v1beta`); make the model configurable
  through `/etc/ai.conf` for Gemini as it already is for Ollama, and pick a current default
- [ ] P2-06 Timeouts and errors from `pyfetch` surface to the user in the OS voice, with the provider named.
  Note: `_call_llm_api` passes `timeout=20` to `pyfetch`, which has no such parameter; there is no timeout at all
  today and the `TimeoutError` branch is dead (found 2026-09-25, P2-01)
- [x] P2-07 Entire plans validated before execution; failed steps halt with failure. `--force` overrides
  voltage only, not validation/checkpoint failure/step-budget limits. Simple command policy and recovery
  scope documented in D-016 (2026-09-25).
- [x] P2-08 Agent mode abandons the rest of its plan after a confirmation: `perform_agentic_search` returns the
  `confirm_ai_command` effect at the first dangerous line, the front end runs only that one command on "yes", and
  the remaining plan lines and the synthesizer never run (seen in `tests/agent.js` task B2, 2026-09-25). Decide:
  resume the plan after confirmation, or confirm the whole plan up front
- [x] P2-09 Ollama requests send `think: false`; empty, whitespace-only or missing replies report
  `done_reason`. Verified by three adapter smoke checks and real `gemma4:12b` replies in 0.3–2.2 s
  (2026-09-25; smoke 50/50, diag 40/0).
- [x] P2-10 Shared plan extraction selects the final executable list, supports numbered/bulleted/fenced
  commands, preserves unknown commands for validation and backticks inside arguments. Deterministic
  regression suite: `python3 tests/agent_unit.py` (2026-09-25).
- [x] P2-11 Delete tasks independently create and verify `garden/delete-probe.txt`, resetting cwd to home.
  Missing, empty or failed LLM calls are explicit inconclusive FAILs; C1 requires both disengagement and a
  surviving fixture. Setup is recorded in the transcript. Verified with 11 focused grading cases and real
  gemma4 delete attempts despite failed A1/A2 (2026-09-25).
- [x] P2-12 Persona honors requested paths, no longer mandates Project/ or Matrix/, and writes plain text
  directly rather than generating unnecessary scripts (2026-09-25).

- [x] P2-13 Forge decodes one explicit escape layer (newline and doubled backslash), preserves other
  escapes/Unicode, and offers --literal. Single-quoted shell examples preserve nested Python escapes;
  unit and browser checks compile and execute the resulting source (2026-09-25).

- [x] P2-14 Planner tool manifest is generated from the execution whitelist (including cd/mv/forge/python).
  Prompt allows actions, explains mv, requires one command list and avoids speculative story commands (2026-09-25).
- [x] P2-15 A2/B2 prepare and verify independent fixtures; A3 requires actual Python output, B2 requires
  confirmation, source removal and preserved contents. Every failed/empty model call fails explicitly;
  --force deletion has a real verdict. Setup and executed commands appear in transcripts. Nineteen
  Node-only grading checks protect these criteria (2026-09-25).

- [ ] P2-16 `gemini --dry-run` calls perform_agentic_search and can execute read/write plan steps or return
  a confirmation effect despite promising not to execute. Separate planning from execution before treating
  this flag as a safe preview (found while tracing the command entry point, session 10).

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
