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

## Open questions

- Q-001 Is the agent's command whitelist meant to grow toward "anything a user can do", with voltage and the
  audit log as the safety net, or stay a curated list? The two halves of `ai_manager.py` (planner manifest of
  17 read-only commands vs. `COMMAND_WHITELIST` with `rm`, `mv`, `forge`, `run`, `chmod`) currently disagree.
- ~~Q-002 Should `main` be replaced with the rewritten history now or later?~~ Done the same day (D-005).
- Q-003 Milestone 1 (AI Town Manager): what "long-term memory" means concretely. See P3-01.
