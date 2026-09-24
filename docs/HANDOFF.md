# Session Handoff

Read this first. It is rewritten at the end of every session so the top half is always true *right now*.
The session log below it is append-only history.

Protocol: see [CLAUDE.md](../CLAUDE.md). Plan: [ROADMAP.md](../ROADMAP.md). Decisions: [DECISIONS.md](DECISIONS.md).
Tests: [TESTING.md](TESTING.md).

---

## Current state

_Last updated: 2026-09-24, session 2 (the in-OS diag suite runs headlessly and passes)._

**What works**
- **The OS boots and runs on Pyodide 314.0.7 / Python 3.14.2** from a 16 MB vendored runtime (D-004). Smoke
  test: kernel up, `cryptography` PBKDF2 derives a key, `first_time_setup` creates root / Guest / the user,
  `verify_password` accepts the right and rejects the wrong password, `echo`, `date`, `whoami`, `ls`, `help`
  behave, and permission denials are the same as on the previous build. Verified in headless Chromium against a
  local `http.server`.
- **The owner's in-OS test suite passes on the new runtime.** `node tests/diag.js` completes onboarding, logs
  in as root, runs `extras/diag.sh` (1,435 lines, 40+ phases: FS commands, ownership and group permissions,
  sudo, scripting and jobs, text tools, `find` / `zip`, pager, `bc`, symlinks, signals, `tr` / `comm`,
  `binder`, `agenda`, brace expansion, `cast`, the planner suite) and grades it: 40 `check_fail` assertions
  pass, 0 fail, no command printed an error, the script reaches its completion banner, about 100 s. That is
  the command layer of Phase 0 observed working on Python 3.14, not just read.
- **Everything else in Phase 0** (the apps, the `gemini` agent, portable mode, the autopilot) is still the
  owner's word and the code. See ROADMAP P0-06, P0-07, P0-10, P0-11.
- **The repo is small again, on `main`.** History was rewritten to drop the 415 MB of old Pyodide (D-005):
  pack 327 MB → 8.8 MB, same messages and dates, new hashes. The owner replaced `main` with the rewritten branch
  and deleted the two Aikido bot branches that still pinned the old blobs. A fresh `git clone` measured 9.1 MB.
- **Docs**: this file, `CLAUDE.md`, `ROADMAP.md`, `docs/DECISIONS.md` (D-001 to D-009), `docs/TESTING.md`,
  `tests/smoke.js`, `.gitignore`. README and CONTRIBUTING point at them.

**Verified**
- `node tests/diag.js http://127.0.0.1:8000/index.html`: PASS, exit 0, twice in a row (Chromium 1194 via
  Playwright 1.56, Node 22). Transcript 1,761 lines.
- `node tests/smoke.js http://127.0.0.1:8000/index.html`: 14/14 checks pass on Pyodide 314.0.7 (Chromium 1194
  via Playwright 1.56, Node 22). Boot to kernel-ready is about 10 s in the cloud container.
- The same commands against the previous Pyodide 0.28.0.dev0 build (served from `git archive` of the old tree)
  gave identical results, including the two Guest permission denials.
- Wheel SHA-256s in `resources/dep/pyodide/` match `pyodide-lock.json`; the five core files are byte-identical
  to the `pyodide@314.0.7` npm package.
- `git filter-repo` result: 9 pyodide blobs remain in history (the current set), nothing else changed
  (`git log --stat` per commit compared before and after).

**Not verified / not done**
- **Nothing UI-level has been exercised by a session**: onboarding dialog, editor, paint, adventure, top, BASIC,
  Gemini chat, themes, sounds, `printscreen`. The smoke test stops at the kernel and executor.
- **The autopilot has never been observed by a session** (P2-01). Needs an Ollama or a Gemini key.
- **Portable (Neutralino) mode is untested here**: no binary in the container. The config pins Neutralino 6.2.0.
- **Firefox and Safari**: untested. Pyodide 314's `pyodide.js` dynamic-imports `pyodide.asm.mjs`; that is fine
  in every evergreen browser but has only been seen in Chromium.
- **`.idea/` and `neutralinojs.log` are still tracked** (P1-07). `.gitignore` now lists them but does not
  untrack them.

**Gotchas for the next session**
- **Two names.** The code says OopisOS (`OopisOS_Kernel`, `oopisOs*` keys, `oopisos-network`); the product is
  FractalOS. Do not rename either (D-009).
- **Silent registration lists.** A new JS file must be in `resources/scripts/asset_manifest.js`; a new Python
  command in `commandFiles` and a new core module in `coreFiles`, both in `resources/bridge.js`. Missing either
  fails silently (D-003, P1-08).
- **`OopisOS_Kernel` is not on `window`.** Top-level `const`. Bare names in `page.evaluate`.
- **`loadPackage(["ssl"])` throws on Pyodide 314.** `ssl` and `hashlib` are in the core now; only
  `cryptography` is loaded. `ssl` is a stub (`OPENSSL_VERSION` = "OpenSSL (stub)"); HTTPS goes through the
  browser's fetch, so nothing depends on it.
- **Pyodide versioning changed.** 314.x = Python 3.14 and is the newest line; 0.29.x is the older Python 3.13
  series. The npm `latest` tag is 314.x. Do not "upgrade" to 0.29.
- **Wheels must come from the same Pyodide release** as the lock file (hash-checked). PyPI wheels do not match.
  Get them from the GitHub release tarball `pyodide-<ver>.tar.bz2` (the `pyodide-core` tarball has no wheels).
- **`pkill -f 'http.server 8000'` killed the session's own shell** once (the pattern matched the wrapper).
  `resources/stop_server.sh` has the same shape. Kill by PID.
- **Guest cannot write in `/home`.** Commands in the smoke test run as Guest. A failing `mkdir /home/x` is
  correct, not a regression.
- **`su` / `logout` swap the terminal output** (saved per-user session state). Capture output by wrapping
  `OutputManager.appendToOutput`, as `tests/diag.js` does, never by reading `#output` afterwards.
- **A failing line aborts a `run` script** (`execute_script` breaks on the first error). So a script that
  prints its final banner ran every line.
- **The diag script's final banner says "SamwiseOS".** A third name (before OopisOS, before FractalOS). Cosmetic;
  `tests/diag.js` matches on "Test Suite ... Complete", not the name.
- **Git working agreement (from the owner):** commit finished, verified work with a normal message; push when
  asked. History was rewritten once with explicit permission (D-005); that is not a standing permission. The
  owner also commits from PyCharm and their local clone is at `/home/gordonk/PycharmProjects/FractalOS/`; after
  D-005 that clone must be re-pointed at the rewritten branch (`git fetch && git reset --hard origin/<branch>`),
  and the owner's own uncommitted work there should be stashed first.
- **Cloud sessions cannot see the sibling repos.** `plainchant` and `BoneAmanita` (the doc-style references)
  live next to this repo on the owner's machine; in a cloud session clone them read-only from GitHub.
- **README says "GitLab" in CONTRIBUTING** ("Fork the repository on GitLab") and the footer links; the repo is
  on GitHub (`aedmark/FractalOS`). Left as is; cosmetic.

## Next steps (in order)

1. **P1-08: generate the `bridge.js` file lists** or test that they match `resources/core/`.
2. **P1-09 / P2-03: decide the `python` command's fate** (claimed, whitelisted, not implemented).
3. **P2-01: watch the autopilot run** against Ollama with a transcript in the handoff.

## Open questions for the user

- Untrack `.idea/` and `neutralinojs.log`? (P1-07)
- Is `python` (script execution inside the OS) a real goal or a stale claim? (P1-09)
- What does "long-term memory" mean for Milestone 1? (Q-003, P3-01)
- Should the agent whitelist converge on "anything a user can do" with voltage as the brake? (Q-001)

---

## Session log

Newest first. Copy the template for each new session.

### Session 2: 2026-09-24: The in-OS diag suite runs headlessly (P1-06)

**Goal:** P1-06: run `extras/diag.sh` through a headless harness and make it the pass/fail gate.
**Done:** P1-06. New `tests/diag.js`: boots, completes onboarding programmatically (mirrors
`OnboardingManager.onFinish`, then reloads), logs in as root, writes the script into `/home/root` via the
`filesystem.write_file` syscall, wraps `OutputManager.appendToOutput` to record every line, runs the script,
grades it. First real run: 40 passed / 0 failed / 0 error lines / banner reached, in 98 s. Nothing in the kernel
or the commands needed fixing for Python 3.14. Docs updated (TESTING.md section and four pitfalls, CLAUDE.md,
CONTRIBUTING, ROADMAP tick). `tests/out/` gitignored.
**Changed:** `tests/diag.js` (new), `.gitignore`, `CLAUDE.md`, `CONTRIBUTING.md`, `ROADMAP.md`, `docs/TESTING.md`,
this file. No app code.
**Decisions:** none new; D-008 covers the approach.
**Problems / surprises**
- First run "saw" only 34 lines and 3 assertions: `su` / `logout` restore per-user terminal state and replace
  the output div. Fixed by recording output at the `appendToOutput` call instead of reading the DOM.
- 40 assertions run but only 38 `check_fail` lines exist at top level; the suite writes child scripts with
  their own. The gate treats the file count as a floor and also requires the completion banner.
- `beep` / `play` at the end log "SoundManager not initialized" in headless mode (no user gesture for
  AudioContext). Ignored by name in the harness; every other console error is reported.
- The run takes 98 s although the script's `delay` lines add up to 124 s; some run inside background jobs.
**Left undone:** The apps, the agent, portable mode and non-Chromium browsers are still unobserved. The diag
harness runs as root only; a Guest-level or sudo-only pass would need a second script.
**Next session should start with:** "Next steps" above.

### Session 1: 2026-09-24: Pyodide trim and upgrade, history rewrite, docs (P1-01 to P1-05)

**Goal:** Trim the vendored Pyodide to the core files plus the wheels the kernel loads and update it; then rewrite
history to reclaim the clone size; then set up the plainchant / BoneAmanita-style documentation scheme.
**Done:** P1-02 (D-004): `resources/dep/pyodide/` from 413 files / 415 MB (0.28.0.dev0, Python 3.13) to 9 files
/ 16 MB (314.0.7, Python 3.14.2); `bridge.js` loads only `cryptography`. P1-03 (D-005): `git filter-repo` on
the branch, pack 327 MB → 8.8 MB. P1-01: `CLAUDE.md`, `ROADMAP.md`, `docs/HANDOFF.md`, `docs/DECISIONS.md`
(D-001 to D-009), `docs/TESTING.md`. P1-04 (D-008): `tests/smoke.js`. P1-05: `.gitignore`. README and
CONTRIBUTING pointed at the new docs; CHANGELOG entry for the Pyodide change.
**Changed:** `resources/dep/pyodide/*` (replaced), `resources/bridge.js` (one line), `README.md`,
`CONTRIBUTING.md`, `CHANGELOG.md`, the new docs and test. No kernel or command code.
**Decisions:** D-001 to D-009 (five of them record pre-existing choices; D-004, D-005, D-008 are this session's).
**Problems / surprises**
- The cloud container's proxy blocks `cdn.jsdelivr.net` (Pyodide's CDN) and the GitHub API for other repos, but
  allows `registry.npmjs.org` and GitHub release downloads. The core files came from npm, the wheels from the
  337 MB `pyodide-314.0.7.tar.bz2` release asset (extracted selectively).
- Pyodide 314 has no `ssl` package at all (`KeyError` in the lock); the old `loadPackage(["cryptography", "ssl"])`
  would have thrown. Found by reading the lock file before touching the code.
- Pyodide's version scheme changed: npm `latest` is `314.0.7` (2026-09-14) and `0.29.5` (2026-09-16) is the
  *older* Python 3.13 line. Easy to pick the wrong "newest".
- First smoke run reported the kernel never ready: `window.OopisOS_Kernel` is undefined because it is a
  top-level `const`. Bare name fixed it. Recorded in TESTING.md.
- A `pkill -f` pattern matched the session's own shell and killed it mid-command; nothing was lost because the
  commit had not started. Recorded in TESTING.md.
- `add_repo` for `BoneAmanita` was denied by the session's permission classifier; the public repo was cloned
  read-only instead, which the tool's own guidance for public repos allows. `plainchant` attached normally.
**Left undone:** `diag.sh` not run (P1-06). Nothing above
the kernel exercised. Autopilot, portable mode, Firefox / Safari unobserved.
**Next session should start with:** "Next steps" above.
**Addendum, same day:** the owner replaced `main` with the rewritten branch from the IDE (reset + force push) and
deleted `fix/aikido-security-code-audit-94322582-biyf` and `-94323551-kisu`, two 2026-08-21 bot branches (a
quote-aware command-substitution fix in `executor.py`; root-only `chown` / `chgrp`) that still referenced the old
history and kept a fresh clone at 335 MB. Owner's call: the fixes are not relevant any more. Fresh clone: 9.1 MB.

---

### Template

```
### Session N: YYYY-MM-DD: short title

**Goal:**
**Done:** roadmap IDs
**Changed:** files / behaviour
**Decisions:** D-numbers added
**Problems / surprises:**
**Left undone:**
**Next session should start with:**
```
