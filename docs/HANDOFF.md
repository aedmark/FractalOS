# Session Handoff

Read this first. It is rewritten at the end of every session so the top half is always true *right now*.
The session log below it is append-only history.

Protocol: see [CLAUDE.md](../CLAUDE.md). Plan: [ROADMAP.md](../ROADMAP.md). Decisions: [DECISIONS.md](DECISIONS.md).
Tests: [TESTING.md](TESTING.md).

---

## Current state

_Last updated: 2026-09-24, session 1 (Pyodide trimmed and upgraded, history rewritten, docs created)._

**What works**
- **The OS boots and runs on Pyodide 314.0.7 / Python 3.14.2** from a 16 MB vendored runtime (D-004). Smoke
  test: kernel up, `cryptography` PBKDF2 derives a key, `first_time_setup` creates root / Guest / the user,
  `verify_password` accepts the right and rejects the wrong password, `echo`, `date`, `whoami`, `ls`, `help`
  behave, and permission denials are the same as on the previous build. Verified in headless Chromium against a
  local `http.server`.
- **Everything in Phase 0 of the roadmap** as the owner built it: kernel, VFS, users / groups / sudo, the shell,
  123 commands, the apps, the `gemini` agent with Gemini and Ollama providers, `story` snapshots, portable mode,
  and the BoneAmanita autopilot. See ROADMAP P0-01 to P0-11. Of all that, only what the smoke test touches has
  been observed by a session; the rest is the owner's word and the code.
- **The repo is small again.** History was rewritten to drop the 415 MB of old Pyodide (D-005): pack 327 MB →
  8.8 MB, 7 commits, same messages and dates, new hashes. `claude/gallant-archimedes-m4ylki` carries it.
- **Docs**: this file, `CLAUDE.md`, `ROADMAP.md`, `docs/DECISIONS.md` (D-001 to D-009), `docs/TESTING.md`,
  `tests/smoke.js`, `.gitignore`. README and CONTRIBUTING point at them.

**Verified**
- `node tests/smoke.js http://127.0.0.1:8000/index.html`: 14/14 checks pass on Pyodide 314.0.7 (Chromium 1194
  via Playwright 1.56, Node 22). Boot to kernel-ready is about 10 s in the cloud container.
- The same commands against the previous Pyodide 0.28.0.dev0 build (served from `git archive` of the old tree)
  gave identical results, including the two Guest permission denials.
- Wheel SHA-256s in `resources/dep/pyodide/` match `pyodide-lock.json`; the five core files are byte-identical
  to the `pyodide@314.0.7` npm package.
- `git filter-repo` result: 9 pyodide blobs remain in history (the current set), nothing else changed
  (`git log --stat` per commit compared before and after).

**Not verified / not done**
- **`main` on GitHub still has the fat history.** The rewritten branch is force-pushed; replacing `main` is the
  owner's call (Q-002). Until then a fresh clone of `main` is still 327 MB.
- **Nothing UI-level has been exercised by a session**: onboarding dialog, editor, paint, adventure, top, BASIC,
  Gemini chat, themes, sounds, `printscreen`. The smoke test stops at the kernel and executor.
- **`extras/diag.sh` has not been run** in this doc's lifetime (P1-06). It is the real command-behaviour suite.
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

1. **Owner: replace `main` with the rewritten history** (Q-002, D-005) and re-point the local clone. Every
   collaborator's clone must be re-cloned or hard-reset afterwards. Until then the size win is branch-only.
2. **P1-06: run `extras/diag.sh` headlessly.** Extend `tests/smoke.js` (or a sibling) to finish onboarding as a
   real user, write the script into the VFS with the `_upload_handler` path or `forge`, `run` it, and count
   `CHECK_FAIL: FAILURE` lines. That turns the owner's suite into the pass/fail gate and will surface any Python
   3.14 behaviour changes the smoke test is too shallow to see.
3. **P1-08: generate the `bridge.js` file lists** or test that they match `resources/core/`.
4. **P1-09 / P2-03: decide the `python` command's fate** (claimed, whitelisted, not implemented).
5. **P2-01: watch the autopilot run** against Ollama with a transcript in the handoff.

## Open questions for the user

- Replace `main` now with the rewritten branch, or after the next review? (Q-002)
- Untrack `.idea/` and `neutralinojs.log`? (P1-07)
- Is `python` (script execution inside the OS) a real goal or a stale claim? (P1-09)
- What does "long-term memory" mean for Milestone 1? (Q-003, P3-01)
- Should the agent whitelist converge on "anything a user can do" with voltage as the brake? (Q-001)

---

## Session log

Newest first. Copy the template for each new session.

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
**Left undone:** `main` still carries the old history (owner's call). `diag.sh` not run (P1-06). Nothing above
the kernel exercised. Autopilot, portable mode, Firefox / Safari unobserved.
**Next session should start with:** "Next steps" above.

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
