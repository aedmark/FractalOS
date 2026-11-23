# Session Handoff

Read this first. Rewrite the top half whenever current state changes or work pauses with context another
session needs, so it is always true *right now*; it fits on a screen or two (about 80 lines).
The session log below it is append-only history: the last ten sessions, newest first. Older ones are in
[archive/](archive/README.md).

Protocol: see [AGENTS.md](../AGENTS.md) (`CLAUDE.md` imports it). Plan: [ROADMAP.md](ROADMAP.md).
Decisions: [DECISIONS.md](DECISIONS.md).
Architecture: [ARCHITECTURE.md](ARCHITECTURE.md). Tests: [TESTING.md](TESTING.md). Security:
[SECURITY.md](SECURITY.md). Changes: [CHANGELOG.md](CHANGELOG.md). Dev diary: [devlog.html](devlog.html).

---

## Current state

_Last updated: 2026-11-23, session 58. Adventure validates and opens BoneAmanita exports._

**Session owner:** none. Check `git status` for the current working tree.

**Where things stand, in one paragraph:** FractalOS 1.0.0 is released and Phases 1 to 8 are done. Phase 9
(x86_64 nodes) works in containers but not yet on real hardware (P9-04 to P9-07). Phase 10 brought the project
docs up to the Manifold template and found and fixed two security bugs (P6-05, P2-24). The biggest gap is not
code: nothing since the Phase 6 Pi work has run on a physical machine or in a real Portable build.

**Verified** (2026-11-08, on the working tree committed as `d0277e0`, Arch-based Linux, Node 22.23.4,
Python 3.14.9, headless Chromium from Playwright 1.63 via `NODE_PATH`, `python3 -m http.server` on 127.0.0.1:8000)

Every row was run in sessions 45 to 48 unless it says it was carried over.

| Suite | Result |
| --- | --- |
| `node tests/structure.js` (includes `tools/check_docs.py`) | **PASS**, docs 0 errors, 0 warnings |
| `node tests/smoke.js http://127.0.0.1:8000/index.html` | **88/88** |
| `node tests/diag.js http://127.0.0.1:8000/index.html` | **40/40** `check_fail`, 0 error lines (one expected 404: `deploy.json`) |
| `python3 tests/agent_unit.py` | **39/39** |
| `node tests/agent_grading.js` | **22/22** |
| `node tests/units.js` (all 24 feature suites, including gpio 11/11, hardware 7/7, window manager 7/7) | **PASS 24/24** (session 48) |
| `node tests/deploy_mesh.js` (and `--live`) | PASS, carried over from 2026-10-12 |
| `tests/agent.js` against a real model | not run since 2026-09-27 (archive, session 17) |

**What works**
- **Exported adventures** (P11-09, D-057). Upload the JSON and run `adventure <filename>`. FractalOS checks
  the start, exit destinations, and carried-item references before opening the game.
- **Live companion rehearsal** (P11-02). Gordon verified inventory, the south-exit hint, and Server Closet recall in Samwise Chat.
- **Adventure pickups** (P11-06, D-054). Use the displayed name in commands such as `take brass key`.
  The companion scene includes pickup history with room locations and current inventory (P11-07, P11-08).
- **Companion launcher** (P11-04, D-053). Run `./extras/start_companion.py` from FractalOS. It uses the sibling
  BoneAmanita checkout and derives the agreed browser origin from the web port.
- **Companion pairing and layout** (P11-03, D-052). Adventure uses the shared title bar and companion controls
  use the theme. Masked paste stays in the code field. Pairing hides the code, port, and button in both views
  until a new pairing is required (P11-05).
- **Status bar identity** (P7-18). The bar and terminal prompt use the same user lookup when sessions restore or change.
- **The local BoneAmanita companion** (P11-01, D-051). `adventure --companion` and `samwise --chat --companion`
  share an account-bound pairing in one tab. Chromium exercised both rooms, the lantern, captured scene labels,
  a retry with the same turn ID, plain-text output, and game commands during a disconnect.
- **The OS in a browser tab and in Portable mode** (D-001 to D-003): shell, 152 commands, apps, users, `sudo`,
  packages with checksums (D-044), the `samwise` agent with voltage brakes, the mesh across tabs and through the
  relay.
- **x86_64 appliance roles** (P9-01 to P9-03, D-046): `signal` tested in Debian 12 and 13 containers; `node`
  browser launch in Debian 13; `deploy.json` switches the mesh on.
- **The public landing page** (D-047, revised by the owner in `eed8d5c`).
- **Project memory** (Phase 10): ARCHITECTURE, SECURITY, a docs map, an archive, a docs checker inside the
  structure test.

**Not verified**
- Anything on real hardware or real systemd: the kiosk X session, a headless `node` after first-run setup, WebRTC
  between two machines, the Pi path (`extras/provision_appliance.sh`).
- `gpio` in a real Portable build (P6-05 tested with fakes) and a real Gemini embeddings call (P2-24).
- The `eed8d5c` landing page at the D-047 widths; the landing page in Firefox, Safari, on a phone, with a screen
  reader.

**Known limits:** a `node` needs a screen once for first-run setup (P9-05); the relay and web server are
unauthenticated (P9-06), which the landing page's "unhackable mesh" does not reflect; Ubuntu's `chromium` is a snap
(P9-07); 32-bit x86 is out of scope.

**Gotchas for the next session**
- Playwright is not installed in this repo. Session 45 borrowed `../level0engine/node_modules` with `NODE_PATH`;
  `docs/TESTING.md` has the scratch-directory recipe.
- `node tests/structure.js` now needs `python3` on the path, because it runs `tools/check_docs.py`.
- The Python feature suites end with a `CRITICAL: Filesystem save function not provided` line; read `OK` and the
  exit code instead (TESTING.md).
- Add a session-log entry; never overwrite the one above. Past ten entries, archive the oldest (AGENTS.md).
- Commit and push only when the owner asks, one approval per commit or push (D-049).

## Next steps

Play exported worlds with [the upload workflow](../README.md#play-with-boneamanita).

1. The owner: turn on private vulnerability reporting (Settings, Security) so SECURITY.md's route works (D-050).
2. Try `gpio` in a real Portable build, ideally on a Pi, and one Gemini embedding with a real key. Then P9-04:
   `provision_x64.sh` on a real old laptop or desktop, `--role node` with a screen, then `--headless`.
3. P9-05: let a headless box create its first account.
4. Recheck the landing page at the seven widths after `eed8d5c`, and decide whether "unhackable" stays while
   P9-06 is open. Update its transcripts and version strings with the next release; they are tied to v1.0.0.
5. Devlog entry if requested; multi-machine WAN WebRTC trials; Raspberry Pi hardware trials.

## Open questions for the owner

The ones that block the next steps; the questions live in DECISIONS.md, "Open questions".

None blocks the next steps. Q-001 (how far the agent's whitelist should grow) and Q-003 (what "long-term
memory" means for P3-01) are older and still open.

## Session log

### Session 58: 2026-11-23: Validate the exported Adventure on import

**Goal:** Open a BoneAmanita export and play from its recorded starting room with its inventory.
**Done:** P11-09, D-057. The loader rejects bad starting rooms, exits, and inventory references before launch.
Gordon completed P11-02 in the live browser. Archived session 48.
**Verified:** [OBSERVED] The old command launched all four invalid test inputs. The new command rejects them.
Chromium uploaded the file produced by BoneAmanita, opened The Mill, showed the brass key in inventory,
and reached The Gallery via north. The companion browser test passed. Smoke passed 91/91, diagnostics 40/40,
feature suites 26/26, and structure and docs passed.

### Session 57: 2026-11-23: Attach rooms to Adventure pickups

**Goal:** Give Samwise Chat the source facts to distinguish the key pickup from the lantern pickup.
**Done:** P11-08, D-056. Room records travel in Adventure scenes. The chat turn stays scene-free. Archived session 47.
**Verified:** [OBSERVED] The previous browser packet omitted pickup locations. The updated Chromium fixture
verified both item-room pairs after moving and dropping an item. General smoke passed 91/91, diagnostics 40/40,
and structure and docs passed.
**Not verified:** Chat recall against the updated live service.

### Session 56: 2026-11-23: Record the items taken during Adventure

**Goal:** Supply factual pickup history for plural questions.
**Done:** P11-07, D-055. Adventure records distinct successful pickups and projects them when the scene fits the
size limit. Archived session 46.
**Verified:** [OBSERVED] The prior scene omitted pickup history. The browser regression then verified two
pickups across rooms, a failed take, and a drop. The oversized-history probe preserved the base scene.
General smoke passed 91/91, in-OS diagnostics 40/40, and structure and docs passed.
**Not verified:** Live-model playthrough with the updated companion service.

### Session 55: 2026-11-22: Ground Adventure pickup questions

**Goal:** Make the brass key selectable by its displayed name and report the actual pickup to BoneAmanita.
**Done:** P11-06, D-054. Authored nouns retain precedence. Failed commands leave the last successful take intact.
Adventure suppresses another question submission while a reply is pending. Archived session 45.
**Verified:** [OBSERVED] Chromium reproduced the rejected full-name command before the fix. The companion smoke then
passed with both items carried, a failed take after the key pickup, and one echo for an in-flight question.
General smoke passed 91/91, in-OS diagnostics 40/40, and structure and docs passed.
**Not verified:** Live-model playthrough with the updated companion service.

### Session 54: 2026-11-22: Hide companion pairing controls after connection

**Goal:** Clear the pairing controls from the companion windows once paired.
**Done:** P11-05. Both views follow the browser pairing state. A rejected code restores the form.
Re-pairing to the same session and port preserves the pending turn ID. Archived session 44.
**Verified:** [OBSERVED] The pairing field stayed visible before the fix. Chromium then passed with both
windows open, a newly opened window, and a rejected code followed by re-pairing and retry. General smoke passed
91/91. Structure and documentation passed with 0 errors and warnings.
**Not verified:** Live BoneAmanita model behavior.

### Session 53: 2026-11-22: One-command companion launcher

**Goal:** Replace separate FractalOS and BoneAmanita startup commands with one local launcher.
**Done:** P11-04. The launcher starts the web server, opens its URL, and runs BoneAmanita in the terminal for pairing.
It uses the configured origin and stops its server when BoneAmanita exits. Archived session 43.
**Decisions:** D-053.
**Verified:** [OBSERVED] A pseudo-terminal smoke test used a fake BoneAmanita process and the real static server.
The origin matched, HTTP served the page, and Ctrl+C stopped both. The launcher test verified the browser URL.
Feature suites passed 25/25. Chromium smoke passed 91/91.
**Not verified:** Launching a live model or opening a real desktop browser with the launcher.

### Session 52: 2026-11-22: Companion paste and layout

**Goal:** Fix the window controls, masked pairing-code paste, and form styling in Adventure.
**Done:** P11-03. The terminal paste shortcut stays with its focused input. Adventure uses the standard title bar
and the companion controls use the app theme. Archived session 42.
**Decisions:** D-052.
**Verified:** [OBSERVED] Headless Chromium reproduced the pairing paste failure on the previous tree. After the fix,
masked paste and the two-room companion smoke passed. Primary smoke passed 91/91. Clipboard and window-manager
units passed. The Adventure layout was visually checked at an 850×560 viewport.
**Not verified:** Live model playthrough and other browsers.

### Session 51: 2026-11-22: Status bar identity

**Goal:** Correct the Guest badge after restoring a logged-in session.
**Done:** P7-18. The terminal's prompt refresh supplies the current username to the status bar. Archived session 41.
**Changed:** `terminal_ui.js`, `status_bar_manager.js`, and `tests/smoke.js`.
**Verified:** [OBSERVED] Chromium reproduced Guest on all three new checks before the fix. After the fix, smoke
passed 91/91, including restore, login, and logout. Status bar unit checks passed 7/7.
**Problems / surprises:** The bar's periodic refresh updated the working directory and clock, while the user label remained the initial Guest text.

### Session 50: 2026-11-22: Local BoneAmanita companion

**Goal:** Share one local companion session across Adventure and Samwise Chat.
**Done:** P11-01. The Adventure kernel supplies the visible scene. The two views share a browser client and render dialogue as text. Archived session 40.
**Changed:** `companion.js`, the Adventure and Samwise command and app paths, boot wiring, and `tests/companion_smoke.js`.
**Decisions:** D-051. Gordon approved the fixed IPv4 loopback destination and user-selected ports.
**Verified:** [OBSERVED] Browser companion smoke passed with a fake peer, including native commands during a disconnect. Structure passed, 24/24 feature suites passed, smoke 88/88, and diagnostics 40/40.
**Not verified:** P11-02 live model behavior.
**Problems / surprises:** The first actual pair-button click reached the terminal. Adventure lacked the standard floating app class (D-038).
**Next session should start with:** Play the built-in two rooms against the live companion, then ask about the lantern in chat.

### Session 49: 2026-11-08: Push, and the owner's answers to Q-004 and Q-005

**Contributor:** Claude Code (Opus 5.5), with the owner's answers
**Goal:** Push the four Phase 10 commits, then record the working agreement and the security reporting route.
**Done:** pushed `f006692..54c2750` to `origin/main` (`eed8d5c..54c2750`, fast-forward; nothing to pull). Q-004 and
Q-005 answered. D-049, D-050.
**Changed:** AGENTS.md ("Working agreement" rewritten from the answers; new "Maintainer preferences" with the
Manifold's writing rules); `docs/SECURITY.md` (one reporting route, no promised timelines, and the caveat that the
setting is off); `docs/DECISIONS.md` (D-049, D-050; Q-004 and Q-005 marked answered); ROADMAP notes on P10-05 and
P10-06.
**Decisions:** D-049 direct to `main`, agents commit and push only when asked, dependencies and data deletion
always need the owner's OK, the Manifold's writing rules. D-050 GitHub private vulnerability reporting is the
only route.
**Verified:** `gh api repos/aedmark/FractalOS/private-vulnerability-reporting` returned `{"enabled":false}`;
`tools/check_docs.py` 0 errors, 0 warnings; `node tests/structure.js` PASS. No code changed.
**Not verified:** nothing else to run.
**Problems / surprises:** the reporting route the owner chose is switched off on the repository. Turning it on is
a repository setting, so it was left to the owner (Next steps 1).
**Corrections:** none.
**Left undone:** enabling private vulnerability reporting (the owner).
**Next session should start with:** Next steps 2, the real-hardware trials.

Older sessions, moved whole: sessions 42 to 48 in [the November archive](archive/SESSION_LOG_2026_11.md), sessions 24 to 41 in
[archive/SESSION_LOG_2026_10.md](archive/SESSION_LOG_2026_10.md), sessions 1 to 23 in
[archive/SESSION_LOG_2026_09.md](archive/SESSION_LOG_2026_09.md).

---

### Template

```
### Session N: YYYY-MM-DD: short title

**Contributor:** person or agent/tool
**Goal:**
**Done:** roadmap IDs
**Changed:** files / behaviour
**Decisions:** D-numbers added
**Verified:** tests and their counts; mutation results if performed; for runs that vary, the tally
**Not verified:** checks skipped or environments unavailable
**Problems / surprises:**
**Corrections:** earlier notes (here or in other docs) found wrong, and what was actually true
**Left undone:**
**Next session should start with:**
```
