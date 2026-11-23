# Session log, November 2026

Entries moved whole from [the handoff](../HANDOFF.md).

### Session 48: 2026-11-08: P7-17 the window manager test runs again, and every feature suite has a runner

**Contributor:** Claude Code (Opus 5.5)
**Goal:** Repair `tests/window_manager_unit.js`, broken since 2026-10-08, and put it in a set people run.
**Done:** P7-17.
**Changed:** `tests/window_manager_unit.js` (the mock's `style` gains `setProperty` and `getPropertyValue`; the
body runs in an async function that awaits `openWindow` and exits 1 on failure; test 1 asserts the published
layer insets); new `tests/units.js` (runs every `tests/*_test.py` and `tests/*_unit.js`, grades by exit code,
optional name filter); AGENTS.md (Layout row, "Feature suites" under Running and testing); TESTING, ROADMAP.
`resources/scripts/window_manager.js` is unchanged.
**Decisions:** none. The test was out of date, not the code: both breaking commits were intended behaviour.
**Verified:** `window_manager_unit.js` 7/7. With `_syncLayerInsets()` skipped in `initialize` it fails on "layer
insets published on init"; with registered windows dropped in `openWindow` it fails on "Two open windows" (file
restored, compared byte for byte). `node tests/units.js` PASS 24/24; against the old test copied in as a probe it
fails and prints the `TypeError` (probe deleted). `node tests/structure.js` PASS; docs 0 errors, 0 warnings.
**Not verified:** smoke and diag, since no product code changed; the window manager in a real browser beyond what
smoke covers.
**Problems / surprises:** the old test ran its assertions at the top level and never awaited `openWindow`, so the
window was not registered yet when the next line counted windows. Wrapping it in an async runner with an explicit
exit code is the pattern the other `*_unit.js` files (for example `hardware_unit.js`) already use.
**Corrections:** none.
**Left undone:** Q-004, Q-005.
**Next session should start with:** Q-004 and Q-005 with the owner, then real-hardware trials (Next steps 2).
Q-004 and Q-005 were answered in session 49.

### Session 47: 2026-11-08: P10-07 the living docs follow the template's formats

**Contributor:** Claude Code (Opus 5.5)
**Goal:** Finish Phase 10: the Manifold template's formats in HANDOFF, DECISIONS, TESTING and ROADMAP.
**Done:** P10-07. Phase 10 is complete. New bug P7-17; new held tension T-001.
**Changed:** `docs/HANDOFF.md` (Current state rebuilt: session owner, a one-paragraph summary, a dated Verified
table with commit and environment, What works, Not verified, Gotchas, Open questions for the owner; the
log template gains Contributor, Verified, Not verified, Corrections); `docs/DECISIONS.md` (the fuller format with
Alternatives and Review trigger, the "record pre-existing choices" rule, Held tensions with T-001, open
questions moved from between D-013 and D-014 to the end, text unchanged); `docs/TESTING.md` (a "Does not prove"
column, rows for the mesh relay and feature suites, "Runs that vary"); `docs/ROADMAP.md` (legend with holders and
item-history rules; P7-17).
**Decisions:** none. T-001 proposes the owner as its owner; confirm or reassign.
**Verified:** every `tests/*_test.py` and `tests/*_unit.js` run by exit code: all pass except
`window_manager_unit.js`. Bisected with `git archive` into the scratchpad: passes at `e0a96b9^`, fails from
`e0a96b9` ("One window registered") and from `9c61914` with a `TypeError`. `tools/check_docs.py` 0 errors,
0 warnings; `node tests/structure.js` PASS.
**Not verified:** no code changed, so smoke and diag were not rerun (their rows are from sessions 45 and 46).
**Problems / surprises:** a quick loop over the JS suites reported `window_manager_unit.js` as exit 0 because the
status was read inside a command substitution; rerun on its own it exits 1. Read exit codes one suite at a time.
**Corrections:** none.
**Left undone:** P7-17; Q-004, Q-005.
**Next session should start with:** P7-17 (done in session 48).

### Session 46: 2026-11-08: P2-24 the Gemini key never goes in a URL

**Contributor:** Claude Code (Opus 5.5)
**Goal:** Move the Gemini embeddings key out of the request URL, which session 44 found by reading the code.
**Done:** P2-24.
**Changed:** `resources/core/ai_manager.py` (`_get_embedding`: the key goes in `x-goog-api-key`, as in the chat
call; an empty key returns "Gemini API key is missing." before any request); `tests/agent_unit.py`
(`GeminiKeyTests`, a fake `pyodide.http.pyfetch` that records each request); `docs/CHANGELOG.md` (Security);
ROADMAP, SECURITY.
**Decisions:** none.
**Verified:** `agent_unit.py` 39/39. Putting the key back in the URL fails the header test; removing the empty-key
check fails the missing-key test (both restored, file compared byte for byte). No other `key=` remains in
`resources/core` or `resources/scripts`. Smoke 88/88, diag 40/40 with 0 error lines, structure PASS,
`agent_grading.js` 22/22 (same Playwright and server as session 45).
**Not verified:** a real Gemini embeddings call; the memory search and sleep cycle that use it.
**Problems / surprises:** with no key, the old code sent a request with `key=None` in the URL. Memory search skips
embeddings when there is no key, but the sleep cycle (`consolidate_memory`) does not: on Gemini without a key it
sent one doomed request per memory. It now sends none.
**Left undone:** nothing in P2-24.
**Next session should start with:** Q-004 and Q-005 with the owner, or P10-07.

### Session 45: 2026-11-08: P6-05 `gpio` no longer passes text to the host shell

**Contributor:** Claude Code (Opus 5.5)
**Goal:** Fix the host command injection that session 44 found by reading `gpio.py`.
**Done:** P6-05.
**Changed:** `resources/core/commands/gpio.py` (`_pin`: 1 to 3 digits, normalised, checked in all seven
subcommands that take a pin, before any host string is built); `resources/scripts/hardware_manager.js`
(`isHostSafePin` gates `readPin` and `writePin`, which build their own `gpio read/write` host commands for the
monitor daemon); `tests/gpio_command_test.py`, `tests/hardware_unit.js`; `docs/CHANGELOG.md` (Security);
ROADMAP, ARCHITECTURE, SECURITY.
**Decisions:** none. Pins are refused everywhere, not only before host calls, so browser and Portable modes accept
the same input; a named virtual pin such as `gpio simulate led 1` now fails (nothing in the repo used one).
**Verified:** `tests/gpio_command_test.py` 11/11 and `tests/hardware_unit.js` 7/7; with the check removed from
`gpio.py` two tests fail, and with `isHostSafePin` returning true test 7 fails (both restored). Smoke 88/88, diag
40/40 with 0 error lines, structure PASS, `agent_unit.py` 37/37, `agent_grading.js` 22/22, swarm and mesh-agent
tests OK. Browser runs used Playwright 1.63 from `../level0engine/node_modules` (`NODE_PATH`), against
`python3 -m http.server` on 127.0.0.1:8000.
**Not verified:** a real Portable build, a Pi, the wiringPi `gpio` binary.
**Problems / surprises:** the JS `HardwareManager` built the same host string independently of `gpio.py`, so a
fix in Python alone would have left the monitor daemon's polling path open to any other caller. The diag run's one
console error is the expected 404 for the optional `deploy.json`.
**Left undone:** `host_api.exec_command` still accepts any string; a future caller must check its own input.
**Next session should start with:** P2-24 (done in session 46).

### Session 44: 2026-11-08: Documentation repairs against the updated Manifold template

**Contributor:** Claude Code (Opus 5.5)
**Goal:** Compare FractalOS's docs with the expanded Manifold template in `../the-manifold/`, fix what its
checker refused, then adopt the missing documents and rules.
**Done:** P10-01 to P10-06 (Phase 10 filed this session). D-048. New bugs P6-05 and P2-24; questions Q-004, Q-005.
**Changed:** `docs/HANDOFF.md` (Current state, Next steps, session numbering, three restored entries),
`docs/DECISIONS.md` (D-009 restored, D-048 added, open-question IDs in bold), `docs/ROADMAP.md`,
`docs/CONTRIBUTING.md` and `README.md` (broken relative links), `AGENTS.md` (directory paths instead of `*`
paths in the Layout table, the archiving rule, the stale "124" command count), new `docs/archive/` (sessions 1
to 34, moved whole and checked word for word against the removed text). Then: new `docs/ARCHITECTURE.md`,
`docs/SECURITY.md`, `docs/README.md`, `tools/check_docs.py`; `tests/structure.js` runs the checker; new AGENTS.md
sections and Layout rows; TESTING's structure-test section.
**Decisions:** D-048 records the 2026-09-25 rename that D-009 had argued against.
**Verified:** the Manifold's checker from a scratch copy, 18 errors before and 0 after; `tools/check_docs.py`
0 errors, 0 warnings in 15 files, and it fails on a broken link, a duplicated session, an out-of-order session and
a duplicated roadmap ID (each undone afterwards, files compared byte for byte); `node tests/structure.js` PASS, and
FAIL with a broken link. ARCHITECTURE and SECURITY facts were read from the code at `1ea2afd`.
**Not verified:** no kernel or front-end code changed, so smoke and diag were not run. P6-05 and P2-24 are from
reading, not from running anything.
**Problems / surprises:**
- The 2026-10-06 sessions restarted their numbering at 10, so 12 to 22 were used twice. Each of them had also
  replaced the entry above it instead of adding one, so three entries vanished from the log: the 2026-09-30
  Phase 6 session (logged as "Session 7"), P7-01/P7-02 ("Session 10") and P7-03 ("Session 11"). Later edits
  stripped the headings of seven more (P7-08 to P7-13 and the v1.0.0 release). Recovered the three entries
  whole from `c9be644`, `a68afb8` and `06e0d14`, restored the seven original headings, and renumbered in date
  order: Phase 6 is 23, the 2026-10-06 sessions 24 to 40, and the later ones 40 to 42. Every cross-reference to
  a session number in the docs points at a session numbered 22 or lower, so none needed changing.
- D-009 ("the internal name stays OopisOS") was deleted in `7080c94` when the rename went ahead, leaving two
  citations dangling. Restored and marked superseded by D-048.
- The checker could not read the `AGENTS.md` Layout table's `*` paths or open questions written without bold
  IDs. Both were changed to the checker's conventions rather than the checker to ours.
**Corrections:** Current state said the landing page was uncommitted; it was committed in `97ace3d` on 2026-11-01.
The September session 10 (the real-model 7/7 rerun, 2026-09-25) has no entry, although session 11 and P2-01
in the roadmap cite it; no commit ever had one.
**Left undone:** P10-07; maintainer preferences in AGENTS.md (Q-004); the reporting route (Q-005).
**Next session should start with:** P6-05 (done in session 45).

### Session 43: 2026-11-08: Landing page copy revision (the owner, between sessions)

**Contributor:** the owner (`eed8d5c`, "1.0 Documentation"), logged by session 44
**Changed:** `resources/landing.html`, `resources/landing.css`: page title "A whole system in a browser tab";
a new origin-story introduction (the Fallout-style terminal); plainer capability headings; an "offline-first,
unhackable" mesh line in the who-it-is-for list; sans-serif body text with monospace kept for headings, chrome
and code; the owner's full name in the footer.
**Not verified:** not viewed at the D-047 widths after the change.

### Session 42: 2026-11-01: Public landing page rebuild

**Goal:** Replace the generic green-on-black landing page with a front door that sells FractalOS to people already looking for a local-first, Python-in-the-browser, AI-and-mesh machine, while still being understandable to someone who has never opened a terminal.
**Done:** D-047. Rebuilt `resources/landing.html` as an EGA product sheet: plain-English explanation and a first-five-minutes card; a tabbed tour with real `whoami`, `ls`, `df -h`, `help python` and CPython 3.14.2 output, an abridged real Samwise autopilot run, and a clearly labelled illustrative mesh transcript; seven capabilities; who-it-is-for and not-for lists; browser, Neutralino and x86_64 appliance paths on a printed quick-start card; an architecture diagram, effect contract, spec table and glossary; ten FAQ answers; and a final boot panel. Added `landing.css` and `landing.js` (no dependencies, no web fonts). Fixed stale claims: v1.0 to v1.0.0, Ollama as well as Gemini, the opt-in mesh, and the non-existent `uname` example.
**Changed:** `resources/landing.html`, `resources/landing.css`, `resources/landing.js`, `README.md`, `AGENTS.md`, `docs/DECISIONS.md`, `docs/CHANGELOG.md`, `docs/HANDOFF.md`.
**Decisions:** D-047.
**Problems / surprises:**
- The old page's `uname -a` transcript was fiction; `uname` is not a command. Replaced it with captured output from the running v1.0.0 build (`whoami`, `ls /`, `df -h`, `help python`).
- At 1200px the hero terminal's Python line was two characters too wide and showed a scrollbar; a 961–1280px font step fixed it. Mobile code blocks now wrap instead of showing scrollbars.
- The boot button has two layouts to serve: `landing.html` beside `index.html` in a checkout, and the published root page with the OS under `os/`. `landing.js` picks `./index.html` for the former and `./os/index.html` for the latter.
**Left undone:** The landing page is not committed. Firefox, Safari, a physical phone and a screen reader were not exercised.
**Next session should start with:** committing the landing page if approved, then P9-04 on real hardware.
