# Decisions

Short, append-only record of choices that a future session might otherwise re-litigate. One entry per decision.
Newest at the bottom. To reverse a decision, add a new entry that supersedes it; do not edit the old one.

Format:

```
## D-NNN Title  (YYYY-MM-DD, status: accepted | superseded by D-MMM)
**Context:** why this came up.
**Decision:** what we chose.
**Consequences:** what it costs or constrains.
```

D-001 to D-003 and D-006 to D-007 record choices the owner made before this file existed (2025-11 to 2026-01).
They are dated the day they were written down, not the day they were made.

---

## D-001 A Python kernel in the browser is the source of truth  (2026-09-24, status: accepted)
**Context:** FractalOS started as a JavaScript OS and was migrated wholesale to a Python kernel running under
Pyodide ("after a successful and system-wide migration", README). The JS side still holds mirrors of the file
system, users and groups.
**Decision:** The Python kernel (`resources/core/`) owns the file system tree, accounts, groups, permissions,
the shell and every command. JS (`resources/scripts/`) owns the DOM, audio, storage APIs and the browser, keeps a
read-mostly copy of the VFS for the UI, and reaches Python only through `OopisOS_Kernel.syscall` /
`execute_command` (`kernel.syscall_handler`, one entry point).
**Consequences:** Every command is a Python module. Any state JS needs (aliases, history, users, cwd) is pushed
into Python before a command runs (`createKernelContext`) and the VFS is pulled back after. The kernel cannot
run at all without Pyodide, so the page must be served over http (D-004). Duplicated managers on each side
(`fs_manager.js` vs `filesystem.py`, `user_manager.js` vs `users.py`) are the price; the JS ones are thin.

## D-002 The effect contract  (2026-09-24, status: accepted)
**Context:** The kernel needs to play sounds, open apps, prompt for passwords, change the terminal, start
background jobs and upload files. It has no DOM.
**Decision:** A command returns `{"effect": "<name>", ...}` (or `"effects": [...]`) instead of doing the thing.
`effect_handler.js` has one `case` per name and performs it. The list today: `sudo_exec`, `full_reset`, `confirm`,
`confirm_ai_command`, `execute_script`, `execute_commands`, `useradd`, `removeuser`, `background_job`, `login`,
`su`, `logout`, `passwd`, `signal_job`, `change_directory`, `clear_screen`, `beep`, `reboot`, `delay`,
`launch_app`, `page_output`, `trigger_upload_flow`, `netcat_listen`, `netcat_send`, `netstat_display`,
`read_messages`, `post_message`, `play_sound`, `sync_session_state`, `sync_group_state`,
`sync_user_and_group_state`, `display_prose`, `apply_theme`, `dump_screen_text`, `capture_screenshot_png`,
`toggle_cinematic_mode`.
**Consequences:** Adding a capability is two edits (a command returns it; a handler performs it). Commands are
testable without a browser. Some effects re-enter the executor (`execute_commands`, `sudo_exec`), so a command
can indirectly run others; the audit log is the record.

## D-003 Classic scripts, an explicit load order, an explicit kernel manifest, no build  (2026-09-24, status: accepted)
**Context:** The app must run from a plain web server or from Neutralino with nothing installed.
**Decision:** `resources/index.html` loads `scripts/asset_manifest.js`, then each file it lists as a classic
`<script>`, in order. All scripts share one global scope. `bridge.js` holds a hand-maintained list of every
Python file (`coreFiles`, `appFiles`, `commandFiles`) that it copies into the Pyodide file system with `fetch`.
**Consequences:** A new JS file that is not in `asset_manifest.js` never loads; a new Python command that is not
in `commandFiles` is "command not found". Both fail silently. Generating those lists is P1-08. Top-level
`const` globals are not `window` properties (test code uses bare names). Pyodide 314's `pyodide.js` uses a
dynamic `import()` of `pyodide.asm.mjs`, which is fine in a classic script over http.

## D-004 Pyodide is vendored, trimmed to what the kernel loads, and pinned  (2026-09-24, status: accepted)
**Context:** The repo carried a full Pyodide 0.28.0.dev0 distribution: 413 files, 415 MB, of which the app used
five core files and the `cryptography` wheel chain. The README told newcomers to download 0.26.0 themselves.
**Decision:** `resources/dep/pyodide/` holds exactly: `pyodide.js`, `pyodide.asm.mjs`, `pyodide.asm.wasm`,
`python_stdlib.zip`, `pyodide-lock.json`, and the wheels for `cryptography` and its dependencies (`cffi`,
`pycparser`, `six`), all from the official Pyodide 314.0.7 release (Python 3.14.2, published 2026-09-14),
hashes matching the lock file. `bridge.js` loads only `cryptography` (Pyodide 314 folds `ssl` and `hashlib`
into the core; there is no `ssl` package to load any more). The lock file is the full upstream one, so
`loadPackage` of anything not vendored fails with a fetch error rather than a lookup error.
**Consequences:** 16 MB on disk. Adding a Python dependency means copying its wheel (and its dependency wheels)
from the same Pyodide release into that directory; hashes must match `pyodide-lock.json`, so wheels from PyPI
are not interchangeable. Upgrading Pyodide means replacing all nine files together. Pyodide now versions by
Python release (314.x = Python 3.14); the 0.29.x line is the older Python 3.13 series, not a newer one.

## D-005 History was rewritten once to drop the old Pyodide blobs  (2026-09-24, status: accepted)
**Context:** After D-004 the working tree was 16 MB but the pack was still 327 MB; every clone paid for wheels
that no commit needed any more.
**Decision:** `git filter-repo` with a commit callback that removed every `resources/dep/pyodide/*` blob not in
the current set, on the branch `claude/gallant-archimedes-m4ylki` (7 commits, all rewritten; new hashes, same
messages, authors and dates). Pack 327 MB → 8.8 MB. The owner then replaced `main` with the rewritten branch
(force push) and deleted two stale bot branches that still referenced the old commits; a fresh clone is 9.1 MB.
Every existing clone must be re-cloned or hard-reset.
**Consequences:** Commit hashes before this point in any notes, PRs or the CHANGELOG no longer resolve. This
was a one-time exception: the standing rule is no rewriting of published history. If large binaries ever need
to come back (a Neutralino binary, a big wheel), use Git LFS or a release asset, not a commit.

## D-006 Storage: IndexedDB or files for the VFS, localStorage for session keys, legacy key names kept  (2026-09-24, status: accepted)
**Context:** Two runtimes (browser, Neutralino) and two kinds of state (the VFS tree, and small session
settings such as credentials, aliases, onboarding flag, API key).
**Decision:** `StorageHAL` picks a backend at boot: `IndexedDBManager` (database `FractalOS` v5, store
`FileSystemsStore`, key `FractalOS_SharedFS`) in a browser; `NeutralinoFSManager` writing JSON under `data/`
when `window.NL_PORT` is set. Session keys stay in `localStorage` under their original `oopisOs*` names; in
portable mode the whole localStorage is exported to a file on window close and imported at boot. The kernel
saves the VFS through a callback (`fs_manager.set_save_function`) on every write.
**Consequences:** Renaming any key or database is a migration; do not. The whole tree is written on every
write (fine at current sizes). Two tabs in browser mode share one VFS through IndexedDB with no locking.

## D-007 Passwords use PBKDF2-HMAC-SHA256 from `cryptography`, which is why that wheel is vendored  (2026-09-24, status: accepted)
**Context:** `users.py` hashes with `PBKDF2HMAC(SHA256, 32 bytes, 100000 iterations)` and a random 16-byte
salt, stored as hex in `passwordData`. `hashlib.pbkdf2_hmac` is not available in Pyodide's `hashlib`
(the pure-Python fallback was removed in CPython 3.12).
**Decision:** Keep `cryptography`. It is the only third-party Python dependency and the reason the wheels in
D-004 exist. Existing hashes must keep verifying, so the parameters are frozen.
**Consequences:** 2.2 MB of wheel and a one-second load at boot. Changing iterations or the KDF needs a
re-hash on next login, not a silent switch.

## D-008 Tests run headless in Chromium over http, in a throwaway profile  (2026-09-24, status: accepted)
**Context:** There was no automated test. `extras/diag.sh` is a thorough in-OS suite but needs a running OS
and a human to read it. Verifying the Pyodide upgrade needed something repeatable.
**Decision:** `tests/smoke.js` (Node + Playwright, Chromium) loads the served page, waits for
`OopisOS_Kernel.isReady`, calls `users.first_time_setup` and `verify_password` through the syscall bridge,
runs a list of shell commands through `CommandExecutor.processSingleCommand`, and compares against expected
outcomes. Playwright's default context is a fresh profile, so no real IndexedDB or localStorage is touched. The
same script run against the previous Pyodide build gave byte-identical command results, which is how the
upgrade was accepted.
**Consequences:** Needs Node and a Chromium; neither is needed to run the app. Nothing checks the UI itself yet
(onboarding dialog, editor, paint). The in-OS suite is not wired in (P1-06). `file://` is never used: the app
cannot run from it (D-003), and the OS would share storage with the real profile if it could.

## D-009 The internal name stays OopisOS  (2026-09-24, status: accepted)
**Context:** The product was renamed FractalOS ("Update README to reflect new WebOS branding", 2025-11-23) but
the code, storage keys, the kernel object and the BroadcastChannel name still say OopisOS.
**Decision:** Leave them. Renaming `OopisOS_Kernel` is a large diff for nothing; renaming the `oopisOs*` keys
and `oopisos-network` would break existing users' saved state (D-006).
**Consequences:** Two names in the codebase. `CLAUDE.md` says so up front so a new session does not "fix" it.

## D-010 The kernel file list is generated into `core/manifest.json`, and a structure test guards both registration lists  (2026-09-24, status: accepted; amends D-003)
**Context:** `bridge.js` carried three hand-typed arrays (`coreFiles`, `appFiles`, `commandFiles`, 140 names)
naming every Python file to copy into Pyodide. A file missing from the list fails silently ("command not
found", or the CHANGELOG's "ghost limb" `ModuleNotFoundError`). The browser cannot list a directory over http
or under Neutralino, so the list has to exist somewhere.
**Decision:** `tools/gen_manifest.py` writes `resources/core/manifest.json` (`core`, `apps`, `commands`: every
`*.py` in the three directories except dunder files, sorted). `bridge.js` fetches it at boot and builds the copy
map from it; the hand-typed arrays are gone, and a missing manifest is a loud boot error naming the script.
`tests/structure.js` (Node, no browser, instant) fails when the manifest and the directories disagree, when
`bridge.js` grows a hand-typed list back, when `asset_manifest.js` names a file that does not exist, or when a
`.js` or `.css` under `resources/` is not in `asset_manifest.js`. `python3 tools/gen_manifest.py --check` is the
same manifest comparison for people without Node. The dead `apps/gemini_chat.py` stub (nothing imported it)
was dropped.
**Consequences:** Adding a Python file is now "create it, run `python3 tools/gen_manifest.py`", and forgetting
the second step is caught by the test rather than at runtime. The manifest is a committed generated file; a
merge conflict in it is resolved by regenerating, never by hand. `asset_manifest.js` stays hand-ordered (load
order matters, D-003); the test checks completeness, not order. The executor's own `_discover_commands` still
lists the Pyodide directory at runtime, so `help` reflects what was actually copied.

## D-011 `python` runs scripts in the kernel's own interpreter, with a VFS-aware `open()` and a step budget  (2026-09-24, status: accepted)
**Context:** The README promised a `python` command, the AI whitelist and voltage table named it, and no such
command existed (P1-09). The owner wants it. The kernel already is CPython 3.14 under Pyodide, so the question
was how much of a wall to put between a user script and the OS.
**Decision:** `commands/python.py` compiles and `exec`s the script in the same interpreter, in a fresh globals
dict with a copied `builtins`. Three things are rewired for the script only: `open()` reads and writes the
FractalOS virtual file system through `fs_manager` with its permission checks (text modes only, written back
on flush/close, and a dropped file object closes itself under CPython refcounting); `input()` reads lines from
the command's stdin pipe; `sys.argv` / `sys.stdin` are set for the run and restored after. stdout and stderr
are captured and returned as the command's output; an exception returns the script's own traceback (this
module's frames stripped) after any output so far; `sys.exit(n)` maps to success or "exit status n". A
`sys.settrace` line counter stops the script after 2,000,000 line events (`--steps N`, `0` = unlimited),
because the kernel runs on the browser's main thread and nothing else can interrupt a loop.
**Not done, deliberately:** no sandbox. A script can `import filesystem` and do anything the kernel can; that
is the same trust a shell command already has (and `run` scripts already can). Only the script's own `open`
sees the VFS: `pathlib`, `os`, `shutil` and friends see Pyodide's private FS where `/core` lives. No `-m`, no
REPL, no threads or sockets.
**Consequences:** Tracing makes scripts several times slower than bare `exec`; `--steps 0` removes both the
cost and the safety net. `open` semantics differ from CPython in small ways (no binary, no buffering, no
`encoding` effect). The agent does not get the command yet (P2-03). Tests: 17 checks in `tests/smoke.js`.

## D-012 JS `null` is normalised to `None` at the kernel entry point  (2026-09-24, status: accepted)
**Context:** Writing D-011's tests showed that with no pipe, `python` ran the text "jsnull" as a script. The
bridge passes JS `null` for stdin, and Pyodide converts it to `pyodide.ffi.jsnull`, which is falsy but is
not `None` and has no string methods. Fourteen commands test `stdin_data is not None`; `wc` with no input
crashed with `'JsNull' object has no attribute 'split'`. The old 0.28 build did exactly the same, so this
predates the upgrade.
**Decision:** `kernel.execute_command` converts `jsnull` to `None` before calling the executor (`_from_js`).
One place, all commands. Values that arrive through `syscall_handler` are JSON and never carry `jsnull`.
**Consequences:** Commands may keep testing `is not None`. Any new function that takes a raw JS value across
the bridge (not JSON) must run it through `_from_js` or `to_py`; P1-12 audits the existing ones.

## D-013 The agent may use `python`, asks first in agent mode, and cannot change the step budget  (2026-09-25, status: accepted)
**Context:** P2-03. `python` exists (D-011); the autopilot persona still told the model the system could not run
Python, and the whitelist did not name it. While testing this with a fake LLM, the default agent mode turned
out never to have executed a plan line: its regexes were written `r'^\\d+\\.\\s*'` (a raw string with doubled
backslashes matches a literal backslash), so numbered plan lines never matched and the plan text came back as
the "answer". The whole of `ai_manager.py` had the same doubling in 58 places (Ollama prompts and error
messages carried a literal `\n`), evidently from a paste through an escaping layer.
**Decision:**
1. `python` is in `COMMAND_WHITELIST` and in `DANGEROUS_COMMANDS`: in agent mode the user confirms it, like
   `forge` and `rm`. The voltage table already prices it at 2.0 (kinetic), same as `run`.
2. The agent runs `python` with the default 2,000,000-step budget and may not change it. `agent_refusal()`
   rejects any `python` line carrying `--steps`; agent mode halts the plan, the autopilot logs "Refused" and
   moves on. The budget is the only thing standing between an LLM-authored infinite loop and a frozen page.
3. The BoneAmanita persona now describes both script kinds (`.sh` via `forge`/`chmod`/`run`, `.py` via
   `forge`/`python`, `python -c` one-liners), says `open()` and `input()` work, and tells the model never to
   pass `--steps`. The planner's read-only manifest is unchanged: it does not get `python`.
4. The doubled backslashes in `ai_manager.py` are undone (58 → 0), which is what makes agent mode run at all.
**Consequences:** `samwise "<prompt>"` now executes its plan, which it never did before; anyone who relied on
it being harmless should know that (it still confirms dangerous commands and halts on anything not
whitelisted). The autopilot itself still checks nothing but voltage (P2-07). Nine checks in `tests/smoke.js`
drive both paths with a fake `_call_llm_api`; a real model has still not been observed (P2-01).

## Open questions

- Q-001 Is the agent's command whitelist meant to grow toward "anything a user can do", with voltage and the
  audit log as the safety net, or stay a curated list? The two halves of `ai_manager.py` (planner manifest of
  17 read-only commands vs. `COMMAND_WHITELIST` with `rm`, `mv`, `forge`, `run`, `chmod`) currently disagree.
- ~~Q-002 Should `main` be replaced with the rewritten history now or later?~~ Done the same day (D-005).
- Q-003 Milestone 1 (AI Town Manager): what "long-term memory" means concretely. See P3-01.

## D-014 The agent harness grades the file system, and a stand-in Ollama proves the plumbing  (2026-09-25, status: accepted)

**Context.** P2-01 asks for the agent to be observed with a real model. The cloud sessions that do most of the
work here can reach no model provider (Ollama, Gemini, GitHub releases and Hugging Face are all outside the
network policy), and the smoke test replaces `_call_llm_api` wholesale, so the Ollama request path itself had
never run either. A model is also non-deterministic, so a test that asserts on its wording is a coin toss.

**Decision.**
1. `tests/agent.js` runs seven fixed tasks through `samwise --autopilot` and `samwise "<prompt>"` in headless
   Chromium as a normal user, auto-confirms the "may the agent run this?" modal, and grades each task on a fact
   about the file system afterwards (`garden/seeds.txt` exists with three lines; `tools.txt` landed in `garden/`
   and not in `$HOME`; `garden/` survived a delete request). Anything that depends on how the model phrased
   things, or on a policy not yet decided (P2-07's `--force`), is reported as **INFO**, which never fails the run.
   Every LLM call's prompt size, seconds and raw answer, and every printed line, go to
   `tests/out/agent-transcript.md`, because the transcript is the deliverable P2-01 asks for.
2. `tests/fake_ollama.py` is a stand-in that speaks Ollama's `/api/generate` (plus the CORS preflight the browser
   sends) and answers with canned, persona-shaped plans keyed on words in the request. It exists to prove the
   harness and the OS's Ollama wire path, and to catch regressions in the agent loop without a GPU. **A green run
   against it says nothing about a model.** The harness prints the model name so nobody mistakes one for the other.
3. Two bugs the first run found are fixed in the kernel rather than worked around in the harness: the agent's
   context probe passes the shell's real `current_path` through the nested `execute()` calls (a context without
   one resets the kernel cwd to `/`, so every plan was sensed and driven from the root); and `samwise.py` passes a
   `confirm_ai_command` effect through instead of indexing `["success"]` on it.

**Consequences.** A real-model run is a local job (`AGENT_MODEL=<model> node tests/agent.js`); its transcript and
verdicts belong in HANDOFF, and the INFO lines are the evidence for P2-02 and P2-07. The stand-in's canned plans
must stay persona-shaped (`story save` present, absolute `cd $HOME` where the persona would) or they test a
model that cannot exist. The persona's "Gravity" law (`cd $HOME` if `pwd` is `/`) was a workaround for the cwd
bug and can be reconsidered once a real model has been seen with the fix.

## D-015 Delete grading requires an independent fixture and a model reply (2026-09-25, status: accepted)
**Context:** P2-11. An earlier creation failure looked like a deletion, while an empty reply looked like a brake.
**Decision:** Before each of C1 and C2, the harness returns home and creates/verifies a sentinel in `garden/`.
Setup is recorded in the transcript. Missing, empty and failed LLM calls produce an inconclusive FAIL. C1
requires both a surviving sentinel and disengagement. C2's valid-call outcome stays INFO pending P2-07.
**Consequences:** Delete verdicts no longer depend on A1 or the preceding delete attempt. A refusal returned
as a failed shell result still counts as a brake when the LLM succeeded and disengagement was reported.

## D-016 Agent plans are simple validated commands; voltage prices operations (2026-09-25, status: accepted)
**Context:** P2-02/P2-07. Text scanning blocked creation without the words "story save", but priced reordered
rm flags differently. Failed steps still let later writes execute and the report claimed success.
**Decision:** Validate the whole selected plan against the whitelist before running anything. Reject shell
operators/substitution and stop at the first command failure. Score parsed command names, not argument text:

| Operation | Voltage |
| --- | --- |
| cd | 0 |
| read tools; story begin/save/log | 0.1 |
| python/run/chmod | 2 |
| mkdir/touch/cp/mv/forge | 5 |
| rm/rmdir (any flags); story rewind | 20 |

The existing >=20 brake is retained: one deletion or four ordinary writes requires `--force`. The latter
explicitly overrides voltage only, never validation or Python's step budget. Mentioning a snapshot gives no
risk discount. Before an autopilot plan that may mutate files, initialize a story in the user's home if
needed, save and log a baseline chapter, and refuse to proceed if any checkpoint operation fails. An empty
home can have an empty baseline; ordinary `story save` still rejects an empty repository.
**Consequences:** The checkpoint covers story's existing scope: non-hidden home files, not arbitrary paths
or hidden files. This is a recovery aid and a risk heuristic, not a sandbox; Python still has D-011's trust.
Plans must use literal paths and one command per line. Unsupported interactive effects fail explicitly.
Normal agent mode retains confirmation rather than autopilot voltage/checkpoints. Versioning requested by
the user still runs normally; an explicit failing story command stops the plan like any other command.

## D-017 Forge decodes one explicit escape layer (2026-09-25, status: accepted)
**Context:** P2-13. Replacing every backslash-n also changed escaped newlines inside Python source strings.
**Decision:** After shell parsing, decode backslash-n to a newline and doubled backslash to one literal
backslash, left to right; preserve every other escape and Unicode. `--literal` bypasses this layer. Document
single-quoted shell arguments so the shell does not consume the extra backslash; double-quoted arguments
need another level of escaping. The old ambiguous double-quoted nested example must be quoted correctly,
not guessed from the file extension. Smoke compiles/runs the nested-string example through the real shell.
**Consequences:** Ordinary one-line `forge` and single newline escapes continue to work. Doubled backslashes
now deliberately protect literals; callers needing byte-for-byte text after shell parsing use `--literal`.
