# Session Handoff

Read this first. It is rewritten at the end of every session so the top half is always true *right now*.
The session log below it is append-only history: the last ten sessions, newest first. Older ones are in
[archive/](archive/README.md).

Protocol: see [AGENTS.md](../AGENTS.md) (`CLAUDE.md` imports it). Plan: [ROADMAP.md](ROADMAP.md).
Decisions: [DECISIONS.md](DECISIONS.md).
Tests: [TESTING.md](TESTING.md). Dev diary: [devlog.html](devlog.html).

---

## Current state

_Last updated: 2026-11-08, session 46, on `main`: P2-24 fixed (the Gemini key in a URL), after P6-05 (session 45)
and session 44's documentation work (Phase 10, P10-01 to P10-06). Those sessions' commits start at `f006692`; check `git status`
for anything not yet committed. Nothing is pushed._

FractalOS 1.0.0, with the rebuilt public landing page (D-047) and Phase 9 x86_64 provisioning (D-046) committed.
- **Public landing page (committed in `97ace3d`, copy revised by the owner in `eed8d5c`):** `resources/landing.html`
  is an EGA product sheet with a plain-English explanation, real captured shell and Python output, an abridged
  Samwise run, capabilities, a who-it-is-for section, three boot paths, the architecture and an FAQ, with
  `landing.css` and `landing.js` beside it; no web fonts or network assets. The `97ace3d` version was checked at
  1440, 1200, 1024, 960, 768, 390 and 320 px with no horizontal overflow, working tabs and copy buttons, and no
  console errors (2026-11-01). The `eed8d5c` revision (new title and intro, capability headings, sans-serif body
  text, the owner's full name) has not been viewed at those widths.
- **Works and tested:** any x86_64 machine that runs a modern browser can be provisioned as a mesh `node`, `signal`
  server or `kiosk` with `extras/provision_x64.sh` (D-046); the `signal` role in Debian 12 and 13 containers (web
  server and relay, two clients exchange broadcast and direct messages); `deploy.json` turning the mesh on in the
  browser (`tests/deploy_mesh.js`, including `--live` through the real relay); a headless Chromium launching under
  the `node` role in Debian 13 (all 2026-10-12, carried over). Smoke 88/88, diag 40/40 `check_fail` with 0 error
  lines, structure PASS, `gpio_command_test.py` 11/11, `hardware_unit.js` 7/7, `agent_unit.py` 37/37
  (2026-11-08, headless Chromium from Playwright 1.63, after P6-05; smoke, diag and structure rerun after P2-24
  with the same results, `agent_unit.py` 39/39).
- **Not tested:** anything on real hardware or under real systemd; the kiosk X session (`xinit` on tty7); a
  headless `node` that has completed onboarding and then joins a mesh; WebRTC data channels across the LAN
  between two machines; the landing page in Firefox, Safari, a physical phone or a screen reader.
- **Known limits:** a `node` needs a screen once for first-run account setup (P9-05); the web server and relay are
  unauthenticated (P9-06), which the landing page's new "unhackable mesh" wording does not reflect; Ubuntu's
  `chromium` is a snap (P9-07); 32-bit x86 is out of scope.
- The Raspberry Pi path (`extras/provision_appliance.sh`) is unchanged and still untested on hardware.
- FractalOS 1.0 documentation (Architectural Codex, `docs/manual/`) is complete (P8-01, D-045).
- **Project docs follow the Manifold template** (Phase 10): new `docs/ARCHITECTURE.md`, `docs/SECURITY.md`,
  `docs/README.md` and `docs/archive/`; new AGENTS.md sections (zones, inquiry rules, protected areas, names,
  environments, an interim working agreement); `tools/check_docs.py`, run by `tests/structure.js`. Left: P10-07
  (format upgrades to HANDOFF, DECISIONS, TESTING) and the owner's answers to Q-004 and Q-005.
- **P6-05 fixed:** `gpio` and `HardwareManager` now send only a numeric pin to the host shell; tested with fake
  host callbacks, not in a real Portable build. **P2-24 fixed:** the Gemini key is sent only as a header; tested
  with a fake `pyfetch`, not against the real API.

## Next steps

1. Q-004 and Q-005 (the owner): the working agreement, and how security problems are reported.
2. P10-07: the remaining template upgrades to the living docs.
3. Try `gpio` in a real Portable build, ideally on a Pi (P6-05 was only tested with fakes), and one Gemini
   embedding with a real key (P2-24). Then P9-04: `provision_x64.sh` on a real old laptop or desktop, `--role node`
   with a screen, then `--headless`.
4. P9-05: let a headless box create its first account.
5. Recheck the landing page at the seven widths after `eed8d5c`, and decide whether "unhackable" stays while
   P9-06 is open. Update its transcripts and version strings with the next release; they are tied to v1.0.0.
6. Devlog entry if requested; multi-machine WAN WebRTC trials; Raspberry Pi hardware trials.

## Session log

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
  order: Phase 6 is 23, the 2026-10-06 sessions 24 to 39, and the later ones 40 to 42. Every cross-reference to
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

### Session 41: 2026-10-12: P9-01..P9-03 x86_64 mesh node / signal server

**Goal:** Give ordinary x86_64 hardware (any machine that runs a modern browser) an install path as a mesh node or signal server, like the Pi had.
**Done:** P9-01, P9-02, P9-03, D-046. New `extras/provision_x64.sh` (roles `signal`, `node`, `kiosk`; `--headless`, `--no-start`, `--uninstall`; systemd units under an unprivileged `fractal` user; system Chromium, no Neutralino). New runtime switch `resources/deploy.json` read by `NetworkManager._applyDeployConfig`. Repaired `extras/signaling_server.py`. New `tests/deploy_mesh.js` (mutation-checked: 7 checks fail with the change reverted).
**Changed:** `extras/provision_x64.sh`, `extras/signaling_server.py`, `resources/scripts/network_manager.js`, `tests/deploy_mesh.js`, `tools/package_release.py` (skips `deploy.json`), `.gitignore`, `README.md`, `AGENTS.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/TESTING.md`, `docs/CHANGELOG.md`, `docs/HANDOFF.md`.
**Decisions:** D-046.
**Problems / surprises:**
- `NETWORKING_ENABLED` was a hard-coded `false` and `/etc/network.conf` only controls a Neutralino-spawned relay, so P6-04 ("peer discovery on boot") could not have worked on any appliance. `deploy.json` is the fix.
- The Python relay treated `targetId: "broadcast"` as a direct target and silently dropped every broadcast; only the unused Node relay worked. Found by the container test, not by reading.
- First run shows onboarding, which returns before `startNetworking()`, so a freshly provisioned headless node never joins. Hence the "screen once" limit.
**Left undone:** P9-04..P9-07. Nothing committed. Real-hardware and real-systemd testing.
**Next session should start with:** committing this work if approved, then P9-04 on a physical machine.

### Session 40: 2026-10-07: P8-01 The FractalOS 1.0 Architectural Codex & Manual (`docs/manual/`)

**Goal:** Overhaul and modernize the legacy 101-page OopisOS manual into the comprehensive FractalOS 1.0 Architectural Codex and User Guide in `docs/manual/`.
**Done:** P8-01, D-045. Authored a complete offline, zero-dependency HTML documentation suite under `docs/manual/`:
- Created `docs/manual/manual.css` with responsive layout, custom typography, callouts, and print styles.
- Created `docs/manual/index.html` detailing Books I–VI and VIII–X with deep architectural analyses, ASCII flowcharts, the Effect Contract, the Voltage Safety Framework, WebRTC mesh protocols, and test engineering.
- Created `docs/manual/commands.html` documenting all 151 native Python commands across 18 functional categories with exact synopsis, flags, execution tracing, and architectural patterns (What It Does, How It Works, Why It Works).
- Verified 100% of internal and cross-file anchor links (52 in index, 320 in commands, 151 cross-links, 0 broken).
- Verified `node tests/structure.js` and `python3 tests/agent_unit.py`.
**Changed:** `docs/manual/manual.css`, `docs/manual/index.html`, `docs/manual/commands.html`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/HANDOFF.md`.
**Decisions:** D-045 (Architectural Codex & HTML Manual).
**Problems / surprises:**
- The command set grew from ~50 JavaScript commands in OopisOS v5.0 to 151 native Python commands in FractalOS 1.0. Decoupled the exhaustive 151-command reference into `commands.html` with cross-links from `index.html` to ensure optimal performance and browsing experience.
**Left undone:** Hardware testing on real Raspberry Pi boards.
**Next session should start with:** Hardware trials, WAN mesh testing, or devlog update.


### Session 39: 2026-10-06: FractalOS 1.0.0 Official Release, Documentation & Packaging

**Goal:** Package official v1.0.0 release bundles, publish devlog and release notes, update README and public-facing documentation, and publish GitHub release.
**Done:** Bumped `OS.VERSION` to `"1.0.0"` in `resources/scripts/config.js` and `neutralino.config.json`. Authored devlog entry in `docs/devlog.html` celebrating FractalOS 1.0.0. Created packaging pipeline `tools/package_release.py` producing `fractalos-1.0.0-web.zip`, `fractalos-1.0.0-web.tar.gz`, `fractalos-1.0.0-appliance.tar.gz`, `fractalos-1.0.0-full.tar.gz`, and `SHA256SUMS` in `dist/`. Tagged git `v1.0.0` and pushed to remote. Updated `README.md` with complete hybrid architecture breakdown, three deployment modes (Browser, Portable Neutralino, Bare-metal Raspberry Pi Appliance), feature breakdown, graphical applications table, and full 151-command system reference table. Updated `docs/CHANGELOG.md` organizing all Phase 6 & Phase 7 capabilities under `[1.0.0]`. Updated `docs/CONTRIBUTING.md` with GitHub repository references and Pull Request conventions. Published GitHub release `v1.0.0` with assets via `gh release create`.
**Changed:** `README.md`, `docs/CHANGELOG.md`, `docs/CONTRIBUTING.md`, `docs/HANDOFF.md`, `docs/devlog.html`, `resources/scripts/config.js`, `neutralino.config.json`, `tools/package_release.py`, `dist/*`.
**Decisions:** Documented and frozen v1.0.0 architecture.
**Problems / surprises:**
- Command reference in `README.md` was missing over 30 commands introduced in recent phases (swarms, mesh, window manager, split panes, status, clipboard, packages). Generated a comprehensive 151-command table with accurate summaries.
**Left undone:** Physical hardware trials on real Raspberry Pi boards.
**Next session should start with:** Community issue triage, hardware testing, or Phase 8 planning.


### Session 38: 2026-10-06: P7-16 Package Security & Sandboxing (`pkg verify`, `pkg audit`, integrity checks, permission scopes)

**Goal:** Implement P7-16: Verification hashes and permission scopes for installed third-party packages before execution.
**Done:** P7-16, D-044. Milestone 7.4 is 100% complete! Upgraded `resources/core/commands/pkg.py` with cryptographic SHA256 checksum tracking across `.fpkg` archives, repository indexes (`index.json`), and `/etc/pkg_manifest.json`. Added checksum verification at installation time (rejecting corrupted or tampered bundles unless overridden with `--skip-verify` or `--force`). Implemented `pkg verify [name]` (`pkg check`, `pkg integrity`) to inspect installed packages on disk in `/etc/packages/commands/{name}.py` against recorded manifest hashes, outputting verified vs tampered diagnostics in text or JSON (`--json`). Updated `resources/core/executor.py` so `_load_command_module` prioritizes VFS package nodes directly, recalculates their SHA256 checksums before execution against `/etc/pkg_manifest.json`, and raises `SecurityError` to block execution of altered or corrupted files. Added permission scope modeling (`metadata()["permissions"]`) with elevated scopes (`root`, `fs:system`, `hardware`) requiring explicit operator authorization via `--trust` (`-t`) or `--force`. Created `pkg audit [name|file]` (`pkg sec`, `pkg security`) using Python standard `ast` to perform static security analysis, detecting dynamic code evaluation (`eval`, `exec`, `compile`, `__import__`), OS process calls (`.system()`, `.popen()`), sensitive filesystem paths (`/etc/`, `/proc/`, `/dev/`), and calculating risk levels (`SAFE`, `LOW RISK`, `MODERATE RISK`, `HIGH RISK`). Created unit test suite `tests/pkg_security_test.py` (6/6 passing in 0.010s). Verified 85/85 smoke checks, structure tests, and all unit test suites.
**Changed:** `resources/core/commands/pkg.py`, `resources/core/executor.py`, `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `tests/pkg_security_test.py`.
**Decisions:** D-044 (Package Security, Cryptographic Verification & Sandboxing).
**Problems / surprises:**
- In `executor.py`, user packages loaded into `sys.modules` previously cached the module in memory, which bypassed disk checks on subsequent runs if the file on disk was modified. Solved by prioritizing VFS package files in `_load_command_module` before `importlib` and performing cryptographic SHA256 integrity verification on every user package load.
- In `pkg.py`, elevated scopes (`root`, `hardware`, `fs:system`) are enforced for all installations unless `--trust` or `--force` is explicitly provided, preventing accidental installation of privileged packages.
**Left undone:** Bare-metal Raspberry Pi testing once hardware is accessible.
**Next session should start with:** Multi-node mesh trials, hardware appliance tests, or devlog update.

### Session 37: 2026-10-06: P7-15 Standard Library Expansion (`fortune`, `cowsay`, `cal`, `banner`)

**Goal:** Implement P7-15: Add classic utilities and games (e.g., `fortune`, `cowsay`, `cal`, `banner`) as installable community packages with documentation and examples.
**Done:** P7-15, D-043. Authored four standard library community packages in `extras/packages/`: `fortune.py`, `cowsay.py`, `cal.py`, and `banner.py`. Each package includes full metadata, flags definition, async `run`, `man`, and `help`. Handled ANSI rendering conventions (D-023) with plain text by default and `-C` / `--color` flags, plus ANSI escape code stripping in `cowsay.py`'s speech bubble width calculations to prevent border distortion when receiving colored piped input. Packaged the community standard library into `resources/core/standard_packages.py`, integrated resolution fallbacks into `resources/core/commands/pkg.py` (`_find_package_source_content` and `pkg search`), and added default VFS paths `/var/pkg/repo` and `/etc/packages/commands` in `resources/core/filesystem.py`. Created test suite `tests/stdlib_packages_test.py` covering searching, installing, executing, flag options, ANSI handling, piped composition (`fortune | cowsay`), and dependency listing/removal (8/8 passing in 0.013s). Regenerated `core/manifest.json` (15 core, 6 apps, 152 commands). Verified 85/85 smoke checks, structure tests, and all unit test suites.
**Changed:** `extras/packages/fortune.py`, `extras/packages/cowsay.py`, `extras/packages/cal.py`, `extras/packages/banner.py`, `resources/core/standard_packages.py`, `resources/core/commands/pkg.py`, `resources/core/filesystem.py`, `resources/core/manifest.json`, `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `tests/stdlib_packages_test.py`.
**Decisions:** D-043 (Standard Library Community Packages).
**Problems / surprises:**
- In `cowsay.py`, piped ANSI color codes from upstream commands (like `fortune -C`) previously caused speech bubble borders to misalign due to raw byte lengths in `textwrap.wrap` and padding. Resolved by adding `_strip_ansi` and `_visible_len` so padding and column calculations consider only printable characters.
- In `filesystem.py`, provisioned default directories `/var/pkg/repo` and `/etc/packages/commands` to ensure clean package repository operations even before initial package publication.
**Left undone:** P7-16 (Package Security & Sandboxing).
**Next session should start with:** P7-16: Package Security & Sandboxing.

Older sessions, moved whole: sessions 24 to 36 in
[archive/SESSION_LOG_2026_10.md](archive/SESSION_LOG_2026_10.md), sessions 1 to 23 in
[archive/SESSION_LOG_2026_09.md](archive/SESSION_LOG_2026_09.md).

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
