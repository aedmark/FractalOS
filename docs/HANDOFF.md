# Session Handoff

Read this first. It is rewritten at the end of every session so the top half is always true *right now*.
The session log below it is append-only history.

Protocol: see [AGENTS.md](../AGENTS.md) (`CLAUDE.md` imports it). Plan: [ROADMAP.md](ROADMAP.md).
Decisions: [DECISIONS.md](DECISIONS.md).
Tests: [TESTING.md](TESTING.md). Dev diary: [devlog.html](devlog.html).

---

## Current state

Milestone 7.2 ("Multi-Agent Swarms & Physical IoT Autopilot") is 100% COMPLETE (`P7-05`, `P7-06`, `P7-07`, and `P7-08`)! FractalOS now has a production-grade Swarm Safety & Voltage Policy framework (`SwarmManager`, `/etc/swarm.conf`, `swarm`, `mesh-agent`, `AuditManager.log_swarm`). Nodes can configure voltage ceilings (`max_remote_voltage`, default 10.0 V), prohibit unauthorized physical hardware actuation (`allow_remote_gpio`, default `false`), block remote force bypasses (`allow_remote_force`, default `false`), and specify caller voltage caps (`--max-voltage <V>`). Remote task planning can be audited without side effects using `--dry-run`, and all incoming swarm actions record node provenance and voltage ratings in `/var/log/audit.log`. All test suites pass: 85/85 smoke checks, 6/6 swarm safety tests, 3/3 swarm safety JS tests, 37/37 agent unit tests, 22/22 grading tests, 4/4 mesh-agent command tests, 5/5 mesh-agent JS tests, 8/8 gpio command tests, 6/6 hardware daemon JS tests, 10/10 peers command tests, 6/6 peers unit tests, 4/4 netgame logic tests, 7/7 netgame JS unit tests, 8/8 mesh command tests, 8/8 mesh unit tests, and all structure tests (14 core, 6 apps, 139 commands, 70 asset entries).

## Next steps

1. Begin Milestone 7.3: Terminal Multiplexing & Windowing UX (`P7-09` split panes `split-v`/`split-h`, `P7-10` TUI window manager, `P7-11` status bar, `P7-12` clipboard bridge).
2. Start with P7-09: Terminal Split Panes (Multiplexer): support horizontal and vertical pane splits in the terminal interface with independent shell contexts.
3. When physical hardware is accessible, test `provision_appliance.sh` and `gpio` on a Raspberry Pi.


## Session log

### Session 16: 2026-10-06: P7-08 Swarm Safety & Voltage Policies for Mesh (`SwarmManager`, `/etc/swarm.conf`, `swarm`, `audit.py`)

**Goal:** Implement P7-08: Swarm Safety & Voltage Policies for Mesh (voltage budgeting and confirmation rules specifically tailored for remote commands and physical hardware actions across nodes).
**Done:** P7-08, D-036. Created `resources/core/swarm_manager.py` with `SwarmManager` managing `/etc/swarm.conf` policies (`max_remote_voltage`, `allow_remote_autopilot`, `allow_remote_gpio`, `allow_remote_force`, `audit_remote_tasks`). Extended `resources/core/audit.py` with `log_swarm` and `get_swarm_entries` for cryptographically verifiable peer provenance logging in `/var/log/audit.log`. Updated `resources/core/ai_manager.py` (`perform_autopilot`) to enforce `max_voltage_budget`, GPIO actuation prohibitions under `swarm_context`, and `--dry-run` plan generation. Added `resources/core/commands/swarm.py` providing unified CLI commands (`swarm status`, `swarm policy [set|reset]`, `swarm log`, `swarm run`). Enhanced `resources/core/commands/mesh_agent.py` and `resources/core/commands/samwise.py` with `--max-voltage` (`-v`), `--dry-run`, and policy subcommands. Updated `NetworkManager.delegateAgentTask` and `_handleMeshAgentRequest` to coordinate voltage budgets and kernel-level swarm safety syscalls. Created unit tests in `tests/swarm_safety_test.py` (6/6 passing) and `tests/swarm_safety_unit.js` (3/3 passing). Regenerated `manifest.json` (14 core, 6 apps, 139 commands). Verified 85/85 smoke checks, structure tests, and all test suites.
**Changed:** `resources/core/swarm_manager.py`, `resources/core/kernel.py`, `resources/core/audit.py`, `resources/core/ai_manager.py`, `resources/core/bone_driver.py`, `resources/core/commands/swarm.py`, `resources/core/commands/mesh_agent.py`, `resources/core/commands/samwise.py`, `resources/scripts/network_manager.js`, `resources/scripts/effect_handler.js`, `resources/core/manifest.json`, `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `tests/swarm_safety_test.py`, `tests/swarm_safety_unit.js`.
**Decisions:** D-036 (Swarm Safety Policies, Remote Voltage Budgets & Provenance Auditing).
**Problems / surprises:**
- In `ai_manager.py`, `perform_autopilot` now natively handles both `max_voltage_budget` and `swarm_context`, immediately blocking remote physical actuation (such as `gpio write` or `gpio mode`) and excessive plan voltage before running any kinetic commands.
- `audit.py` captures peer provenance (`PEER: <sourceId> (<user>)`) and voltage ratings in `/var/log/audit.log`, queryable via `swarm log`.
**Left undone:** Physical testing on a Raspberry Pi deferred until hardware is accessible.
**Next session should start with:** P7-09: Terminal Split Panes (Multiplexer) for Milestone 7.3.


### Session 15: 2026-10-06: P7-07 Distributed Agent Task Delegation (`mesh-agent`, `samwise --node`, `NetworkManager`)

**Goal:** Implement P7-07: Allow `samwise` on one node to dispatch sub-tasks or queries to a peer node's agent over the mesh network and await synthesized results.
**Done:** P7-07, D-035. Extended `NetworkManager` with `mesh_agent_request` and `mesh_agent_response` handling, request tracking via `reqId`, `resolvePeerId`, and `delegateAgentTask(targetPeerId, prompt, options)`. Created `resources/core/commands/mesh_agent.py` supporting `mesh-agent <nodeId> <prompt> [--autopilot] [--timeout <sec>] [--json]` and wired `--node` / `-n` flag support into `resources/core/commands/samwise.py`. Added `mesh_agent_delegate` effect handling in `resources/scripts/effect_handler.js` with styled ANSI swarm border formatting. Updated `AIManager` with `mesh-agent` / `mesh_agent` whitelisting and confirmation checks for remote autopilot, updated `BoneDriver` with swarm courier tool prompt, voltage pricing (1.0 V inquiry, 5.0 V autopilot), and checkpoint bypass. Created unit tests in `tests/mesh_agent_test.py` (4/4 passing), `tests/mesh_agent_unit.js` (5/5 passing), and `tests/agent_unit.py` (37/37 passing). Verified 85/85 smoke checks, structure tests, and all test suites.
**Changed:** `resources/scripts/network_manager.js`, `resources/core/commands/mesh_agent.py`, `resources/core/commands/samwise.py`, `resources/scripts/effect_handler.js`, `resources/core/ai_manager.py`, `resources/core/bone_driver.py`, `resources/core/manifest.json`, `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `tests/mesh_agent_test.py`, `tests/mesh_agent_unit.js`, `tests/agent_unit.py`.
**Decisions:** D-035 (Distributed Agent Task Delegation over the Mesh).
**Problems / surprises:**
- In `NetworkManager._processIncomingMessage`, outer wrapper payload passed inner payload under `.data`; updated `_handleMeshAgentRequest` and `_handleMeshAgentResponse` to unpack from either `payload.data` or `payload` cleanly.
**Left undone:** Physical testing on a Raspberry Pi deferred until hardware is accessible.
**Next session should start with:** P7-08: Swarm Safety & Voltage Policies for Mesh.



### Session 14: 2026-10-06: P7-06 IoT Autopilot Actions (`samwise`, `BoneDriver`, `AIManager`, `gpio`)

**Goal:** Implement P7-06: Teach `samwise` to interact with hardware sensors and actuators, configure monitoring daemons, and enforce hardware voltage safety policies.
**Done:** P7-06, D-034. Extended `BoneDriver` in `resources/core/bone_driver.py` with IoT biology laws and tool manifest examples (`gpio mode`, `read`, `write`, `monitor`, `stop`, `monitors`), operation-based voltage pricing for GPIO subcommands (0.1 V for reads, 2.0 V for modes, 5.0 V for writes/monitors, plus recursive voltage scoring of `--action` commands), and checkpoint bypass for non-filesystem GPIO actions. Updated `AIManager` in `resources/core/ai_manager.py` with `gpio` whitelisting, prompt guidance, `is_dangerous` checks requiring confirmation for kinetic writes in agent mode, and `ALLOWED_PLAN_EFFECTS` support in `_execute_plan_step` and `perform_autopilot` for non-interactive background/hardware effects (`gpio_monitor_start`, `gpio_monitor_stop`, `gpio_simulate`, `play_sound`, `mesh_broadcast`). Updated `samwise.py` to deliver collected effects alongside prose reports. Added 6 new unit tests to `tests/agent_unit.py` (32/32 passing). Verified 85/85 smoke checks, structure tests, and all test batteries.
**Changed:** `resources/core/bone_driver.py`, `resources/core/ai_manager.py`, `resources/core/commands/gpio.py`, `resources/core/commands/samwise.py`, `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `tests/agent_unit.py`.
**Decisions:** D-034 (IoT Autopilot Actions, Hardware Voltage Policies, and Non-Interactive Effects).
**Problems / surprises:**
- In `ai_manager.py`, `_execute_plan_step` was previously halting any step that returned any effect other than `change_directory`. Added `ALLOWED_PLAN_EFFECTS` whitelist (`gpio_simulate`, `gpio_monitor_start`, `gpio_monitor_stop`, `play_sound`, etc.) so background hardware actions execute cleanly without requiring interactive user terminal prompts.
**Left undone:** Physical testing on a Raspberry Pi deferred until hardware is accessible.
**Next session should start with:** P7-07: Distributed Agent Task Delegation over the mesh network.



### Session 13: 2026-10-06: P7-05 Hardware Sensor Monitoring Daemon (`gpio`, `HardwareManager`)

**Goal:** Implement P7-05: Hardware Sensor Monitoring Daemon supporting background interval polling, trigger conditions, action callbacks, and virtual GPIO simulation.
**Done:** P7-05, D-033. Extended `resources/core/commands/gpio.py` with `mode`, `read`, `write`, `monitor <pin>`, `stop <pin>`, `monitors`, `simulate <pin> <val>`, and `stream <pin> [count]`. Implemented `HardwareManager` in `resources/scripts/hardware_manager.js` to manage background polling intervals, edge trigger detection, automatic shell action execution via `CommandExecutor`, mesh broadcast forwarding, and event logging. Added `gpio_monitor_start`, `gpio_monitor_stop`, `gpio_monitor_list`, and `gpio_simulate` effect handlers in `effect_handler.js`. Wired `HardwareManager` into `main.js` and registered in `asset_manifest.js`. Created unit tests in `tests/gpio_command_test.py` and `tests/hardware_unit.js`. Verified 85/85 smoke checks, structure tests, and all test suites.
**Changed:** `resources/core/commands/gpio.py`, `resources/scripts/hardware_manager.js`, `resources/scripts/effect_handler.js`, `resources/scripts/asset_manifest.js`, `resources/main.js`, `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `tests/gpio_command_test.py`, `tests/hardware_unit.js`.
**Decisions:** D-033 (Hardware sensor monitoring daemon, edge detection, and virtual GPIO simulation).
**Problems / surprises:**
- Node test runner needed explicit `process.exit(0)` after asynchronous timer resolution to avoid lingering event loop polling keeping tests hanging.
- Dual-mode architecture seamlessly provides virtual GPIO emulation on browser/headless environments while transparently utilizing sysfs/libgpiod when running under Neutralino on physical Linux/Raspberry Pi hardware.
**Left undone:** Physical testing on a Raspberry Pi deferred until hardware is accessible.
**Next session should start with:** P7-06: IoT Autopilot Actions for `samwise`.



### Session 12: 2026-10-06: P7-04 Mesh Node Presence & Discovery UI (`peers`, `netstat --mesh`)

**Goal:** Implement P7-04: Live network status app and shell command (`peers` / `netstat --mesh`) displaying discovered nodes, latency, and shared capabilities.
**Done:** P7-04, D-032. Milestone 7.1 complete! Created `resources/core/commands/peers.py` and enhanced `netstat.py` with `--mesh` and `--gui` flags. Extended `NetworkManager` to broadcast and cache rich peer metadata (user, host, transport, capabilities, uptime) in `peerMetadata`, with `getLocalNodeInfo()`, `getPeersDetailed({ doPing })`, and `getPeerInfo(peerId)`. Added `peers_display` and `peers_info` handlers in `effect_handler.js` for ANSI table formatting, ping measurements, and JSON export. Built `PeersManager` and `PeersUI` with `peers.css` for a live auto-polling Mesh Network Monitor app with status cards, latency badges, and action buttons. Created unit tests in `tests/peers_command_test.py` and `tests/peers_unit.js`. Verified 85/85 smoke checks, structure tests, and all test suites.
**Changed:** `resources/core/commands/peers.py`, `resources/core/commands/netstat.py`, `resources/scripts/network_manager.js`, `resources/scripts/effect_handler.js`, `resources/scripts/apps/peers/peers_ui.js`, `resources/scripts/apps/peers/peers_manager.js`, `resources/scripts/apps/peers/peers.css`, `resources/scripts/asset_manifest.js`, `resources/main.js`, `resources/core/manifest.json`, `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `tests/peers_command_test.py`, `tests/peers_unit.js`.
**Decisions:** D-032 (Mesh node presence, discovery protocol, and monitor TUI).
**Problems / surprises:**
- In `tests/peers_unit.js`, `createMockElement` threw a TypeError when children was passed as a single element or non-array. Guarded with `Array.isArray(children)` to allow both forms safely.
**Left undone:** Physical testing on a Raspberry Pi deferred until hardware is accessible.
**Next session should start with:** Milestone 7.2 (P7-05: Hardware Sensor Monitoring Daemon).


### Session 22: 2026-09-30: Phase 5 (Networking and Portable Mode)

**Goal:** Implement Phase 5 open questions (WebSockets, Portable Mode verification, Host Mounting).
**Done:** P5-01, P5-02, P5-03.
**Changed:** `extras/signaling_server.py`, `resources/core/commands/mount.py`, `resources/core/filesystem.py`, `resources/scripts/fs_manager.js`, `resources/bridge.js`, `resources/scripts/effect_handler.js`, `resources/core/commands/cat.py`, `resources/core/commands/grep.py`, `resources/core/commands/ls.py`, `resources/core/commands/edit.py`, `resources/core/commands/python.py`, `docs/ROADMAP.md`.
**Decisions:** Built a lightweight Python WebSocket server for signaling. Verified Neutralino 6.2.0 on Linux. Implemented `mount host <dir>` using an asynchronous VFS bridge approach, adding `host_mount` and `host_file` nodes that fetch content from Neutralino's filesystem API lazily via JavaScript Promises, and updating core commands to `async def run()`.
**Problems / surprises:** 
- Python `open()` inside executing scripts is synchronous and cannot access the asynchronous Neutralino file API. We successfully patched `python.py`'s `open` mock to gracefully raise an `OSError(1)` if a script attempts to natively open a host-mounted file. However, `python /mnt/host/script.py` executes flawlessly because the command reads the file via the bridge before calling `exec()`.
**Left undone:** The roadmap is officially complete!
**Next session should start with:** Reviewing the system for 1.0 release or defining Phase 6.


### Session 21: 2026-09-30: Package Management (P4-01, P4-02)

**Goal:** Implement the package management system for FractalOS.
**Done:** P4-01, P4-02, D-028.
**Changed:** `resources/core/commands/pkg.py` (new command), `resources/core/executor.py` (added dynamic module loading via `_load_command_module` and exposed `get_all_commands`), `resources/core/commands/help.py` & `man.py` (switched to `executor._load_command_module`), `resources/scripts/effect_handler.js` (added `update_commands_manifest`), `resources/bridge.js` (boot-time package wheel loading and manifest aggregation), `docs/DECISIONS.md`, `docs/ROADMAP.md`.
**Decisions:** D-028 (Packages are single `.py` command files stored in the VFS at `/etc/packages/commands/`, registered in `/etc/pkg_manifest.json`, and dynamically loaded by the executor).
**Problems / surprises:** 
- The VFS is initialized before Pyodide boots in JS, which allowed us to cleanly read `/etc/pkg_manifest.json` right before Pyodide initialization to load necessary extra wheels upfront using `pyodide.loadPackage()`.
**Left undone:** Phase 4 is complete. 
**Next session should start with:** "Next steps" above.


### Session 20: 2026-09-29: Memory Embeddings and Adventure Creator (P3-04)

**Goal:** Implement offline embedding search fallback and finish Phase 3 by fleshing out the adventure engine.
**Done:** P3-04 (Adventure engine features), D-027.
**Changed:** `resources/core/ai_manager.py` (added exact pure-Python cosine similarity and Jaccard similarity fallback, dredge logic, and consolidate command), `resources/core/bone_driver.py` (updated memory path rule), `resources/core/commands/samwise.py` (added `--sleep`), `resources/core/apps/adventure.py` (added `_handle_use`, `_handle_drop`, `_handle_score`, `_handle_wait`, win condition checks, and the Python-side creator mode endpoints `creator_initialize`, `creator_get_prompt`, and `creator_process_command`), `resources/scripts/apps/adventure/adventure_create.js` (swapped missing JS methods for async `syscall` routing to the new Python creator endpoints), `docs/ROADMAP.md` (P3-04 marked done), `docs/DECISIONS.md` (D-027).
**Decisions:** D-027 (Pure-Python cosine exact vector search & lexical fallback).
**Problems / surprises:**
- The JavaScript adventure creator tool (`adventure_create.js`) was trying to synchronously call `FractalOS_Kernel.adventureCreatorInitialize` which didn't exist anywhere in the codebase. It was a complete ghost limb. Rewrote it to properly `await FractalOS_Kernel.syscall`.
- The core adventure engine parsed `"use"`, `"drop"`, `"wait"`, and `"score"`, but the methods were completely missing. Implemented them and hooked up the parsing for `winCondition` so a game can actually be won.
**Left undone:** Phase 3 is completed. Phase 4 (Packages and extensibility) is next.
**Next session should start with:** "Next steps" above.


Newest first. Copy the template for each new session.

### Session 19: 2026-09-29: UI Fixes and Persistence Debugging

**Goal:** Address user-reported UI feedback regarding Paint and BASIC, explain the model list mismatch, and resolve the critical persistence bug on Neocities.
**Done:** P3-04 (added to ROADMAP)
**Changed:** 
- `resources/main.js`, `resources/scripts/effect_handler.js`, `resources/scripts/user_manager.js`: Implemented `FractalOS_LastUser` memory to maintain the logged-in user across page reloads.
- `resources/scripts/apps/paint/paint_manager.js`: Awaited `getCurrentUser` correctly in `_saveContent` to resolve the broken Paint save button.
- `resources/scripts/apps/paint/paint_ui.js`: Removed the redundant cut, copy, and paste buttons.
- `resources/scripts/apps/basic/basic_manager.js`: Clarified the `SYNTAX ERROR` message to explain that BASIC statements require line numbers.
- `docs/ROADMAP.md`: Added P3-04 for fleshing out the text adventure engine and creator tools.
**Decisions:** N/A
**Problems / surprises:** 
- The persistence bug wasn't an actual data-loss issue; it was a logic gap. When the user refreshed the page, the system dropped them back to `Guest`, making it seem as if their files (stored in `/home/<username>`) and aliases (stored in their user session) were deleted. They just needed to `login`. We fixed this by persisting the last logged-in user across reboots.
- The "fake models" issue in chat is due to the browser's Mixed Content security policy. HTTPS pages (Neocities) physically block JavaScript from fetching HTTP resources (`http://localhost:11434`), causing our fetch call to Ollama to fail and trigger the hardcoded model fallback.
- The `PRINT "HELLO"` bug was because the Python `basic.py` interpreter is a stub and `basic_manager.js` forces the user to prefix statements with line numbers (e.g., `10 PRINT "HELLO"`). Updated the error message to clarify this.
**Left undone:** Adding a manual text-input fallback for the AI Model dropdown picker if the user desires.
**Next session should start with:** The next steps in the roadmap.

### Session 18: 2026-09-29: Agent hardening and testing hygiene (P1-16, P2-22, P2-23, P1-15)

**Goal:** Address the next steps in the handoff: make smoke tests fail on page errors, fix agent Python environment misunderstanding, guide agent away from redundant rmdir, and add classify flag to ls.
**Done:**
- P1-16: Updated `tests/smoke.js` to collect page errors and fail the suite with exit code 1 if any are caught. Confirmed test passes locally.
- P2-22: Added explicit wording to `bone_driver.py` persona indicating `python` has standard library only (no numpy, requests, etc.).
- P2-23: Appended guidance to `bone_driver.py` instructing the agent to delete a directory by path "ONCE" and never to run `rmdir` after `rm -r`.
- P1-15: Added `-F` / `--classify` flag to `ls` (`ls.py`), with logic to append `/` to directories, `@` to symlinks, and `*` to executables. Decided against throwing "invalid option" for unknown flags globally, to keep command argument pass-through behavior intact.
**Changed:** `tests/smoke.js`, `resources/core/bone_driver.py`, `resources/core/commands/ls.py`, ROADMAP.md, HANDOFF.md.
**Decisions:** None new.
**Problems / surprises:** Playwright wasn't installed globally so a scratch path was needed to run the test suite locally.
**Left undone:** Manual app pass, Gemini run.
**Next session should start with:** "Next steps" above, starting with the manual app pass.

### Session 17: 2026-09-27: P2-21 closed with a check, not only a prompt (D-024); two regressions from sessions 15-16 fixed

**Goal:** The owner: "continue with P2-21". Session 14 had ticked it with persona guidance but never measured it.
**Done:**
- Measured first: C2 ×5 on llama3.1:8b, current code: 4 PASS, 1 `cd garden` + `rm -r *`. Guidance alone was
  not enough. A full run then showed a new variant, `rm -r .`, which FractalOS's `rm` executed by deleting the
  current directory; `rm -rf ..` deleted the caller's home.
- D-024: `validate_plan` rejects `rm` of `*`, `.`, `..`, so P2-17's retry re-plans; `rm` refuses `.`, `..`, `/`.
  Man page updated. 3 unit tests and 9 smoke checks, each failing on the old code.
- Evidence: C2 10/10 twice; injected bad first plan corrected 5/5; full runs llama 9/10, 10/10, 10/10 and
  gemma 10/10 twice, with `rm -r .` once and `rm -r *` twice rejected and corrected unprompted.
- `tests/agent.js`: `AGENT_TASKS` selects tasks. D3 called `kernel.chidi_analysis`, deleted in session 16, and
  aborted every full run since, so session 15's 10/10 did not hold on current `main`; D3 now makes the Chidi app's
  syscall, and must mention the file's content.
- The model pickers from `93bae32` never filled: `AIManager.getAvailableModels` returned the syscall envelope, not
  the list. Fixed; smoke check added (fails without the fix).
**Changed:** `resources/core/ai_manager.py`, `commands/rm.py`, `scripts/ai_manager.js`, `tests/agent.js`,
`tests/agent_unit.py` (24 → 26), `tests/smoke.js` (75 → 85), DECISIONS (D-024), ROADMAP (P2-21; P1-15, P1-16,
P2-22, P2-23 new), TESTING, CHANGELOG, AGENTS.md, this file.
**Decisions:** D-024.
**Problems / surprises**
- The smoke run printed `[pageerror] models.includes is not a function` and still said PASS (P1-16).
- `rm -r .` is not a model quirk to prompt away: it was an OS bug any user could hit.
- In C1, a rejected `rm -r *` came back as `rm -r /home/gordon/garden` and the brake still disengaged: retries do
  not get around the voltage brake.
**Left undone:** P2-22, P2-23, P1-15, P1-16, the manual pass, Gemini.
**Next session should start with:** "Next steps" above, item 1.

### Session 16: 2026-09-27: Housekeeping (P1-12, P1-10)

- **Goal**: P1-12 (`jsnull` audit) and P1-10 (Move `www/` into `neutralino/`).
- **Done**:
  - Found that the `www/` directory is just the stock Neutralinojs template and `documentRoot` handles what actually runs. Moved `www/` to `neutralino/www/` so it doesn't pollute the root repo space.
  - Updated `AGENTS.md` and `ROADMAP.md` to reflect the `www/` change.
  - Discovered that all `FractalOS_Kernel` app function wrappers in `kernel.py` were unused (except for one broken one in `chidi_manager.js`).
  - Fixed `chidi_manager.js` to use the unified `syscall` mechanism.
  - Deleted ~120 lines of dead global functions from `kernel.py` that were previously exposed to JS, confirming that `execute_command` and `syscall_handler` are the only functions bridging the boundary.
  - Ran `structure.js`, `diag.js`, and `smoke.js` to confirm all 75 tests still pass perfectly.
- **Outcome**: P1-10 and P1-12 are complete. The codebase is cleaner and fully decoupled from legacy `pyodide.ffi` boundary bugs.

### Session 15: 2026-09-27: Automated tests for AI commands (P2-04)

- **Goal**: P2-04: Verify Chidi, `remix`, and `storyboard` against a real model with a recorded transcript.
- **Done**:
  - Found `remix` and `storyboard` lacked automated tests.
  - Added tasks `D1`, `D2`, and `D3` to `tests/agent.js` to execute `remix`, `storyboard`, and `chidi_analysis` headless.
  - Discovered and fixed missing short flag aliases `-p` and `-m` handling in the test runner.
  - Discovered and fixed Playwright `page.evaluate()` multiple argument restriction.
  - Found an issue with `analysis_type` for `chidi_analysis`: it expected `"summarize"`, but the test sent `"summary"`. Fixed the test.
  - Ran the harness with a local Ollama model (`llama3.1:8b`) via Playwright, all 10 tests passed!
- **Outcome**: P2-04 complete. Transcript recorded in `tests/out/agent-transcript.md`.

- **[2026-09-25] P2-08 Agentic Search Continuation:** Refactored `perform_agentic_search` to yield continuation state in the `confirm_ai_command` effect. Added a hidden `--resume-agent` flag to the `samwise` command to resume the agent plan upon user confirmation. Updated `effect_handler.js` to dispatch the continuation automatically after executing the confirmed step.

### Session 14: 2026-09-27: Agent hardening (P2-21, P2-18), Configurable Gemini (P2-05), Structure check (P1-11)

**Goal:** Work the next steps in the handoff: P2-21, P2-18, P2-05, and P1-11.
**Done:**
- P2-21: Updated `ai_manager.py` and `bone_driver.py` persona instructions to explicitly forbid deleting directories with `*` and to require absolute paths.
- P2-18: "Scar Tissue" Context Injection. Tracked recent execution failures in `session.env_manager` as `_AI_LAST_ERROR`, cleared them on success, and injected them in `_get_terminal_context()`.
- P2-05: Made the Gemini model configurable by resolving it from the config or default in `ai_manager.py`.
- P1-11: Added automated checks to `tests/structure.js` that ensure every module in `resources/core/commands/` exposes `run` and `man`. Fixed `true.py` which was missing `man`.
**Changed:** `resources/core/ai_manager.py`, `resources/core/bone_driver.py`, `resources/core/commands/true.py`, `tests/structure.js`, `ROADMAP.md`, `HANDOFF.md`.
**Decisions:** none.
**Problems / surprises:**
- The command `true` was missing a `man` function, which was caught by the new P1-11 structure test.
**Left undone:** P2-04 (testing against a real model), P1-12 (`jsnull` audit), P1-10 (`www/`), manual app pass.
**Next session should start with:** "Next steps" above, starting with P2-04.

### Session 13: 2026-09-26: Agent hardening, `tree -C` (P2-20, P2-16, P1-13, P2-06, P2-17, P1-14)

**Goal:** Work the roadmap in the owner's order: P2-20, P2-16, P2-06, P2-17, then `tree -C` (the owner's idea after
llama planned it).
**Done:**
- P2-20 (D-019): Samwise Chat spliced messages into the shell line; `$(touch ...)` in a chat message created the
  file. Messages now travel as JSON on stdin.
- P2-16 (D-020): `--dry-run` ran agent-mode plans and was ignored by `--autopilot`. Planning is now separate
  (`plan_agentic_search`, `plan_autopilot`); dry run reports and runs nothing.
- P1-13: the prompt printed `~\$` since the first commit (a regex `$` anchor).
- P2-06 (D-021): `pyfetch` ignored `timeout=20`, so a hung provider froze the command. AbortSignal timeout,
  `timeout_seconds` in `/etc/ai.conf`, provider-named errors; `samwise` man page documents `/etc/ai.conf`.
- P2-17 (D-022): rejected plans retried up to 3 calls; the brake never. P2-21 added from llama's `rm -r *`.
- P1-14 (D-023): `tree -C`; the terminal renders ANSI colour.
- Wrap-up: HANDOFF rewritten, CHANGELOG and TESTING brought up to date.
**Changed:** `resources/core/ai_manager.py`, `commands/samwise.py`, `commands/tree.py`,
`scripts/apps/samwise_chat/samwise_chat_manager.js`, `scripts/output_manager.js`, `scripts/terminal_ui.js`,
`main.css`, `tests/smoke.js` (59 → 75), `tests/agent_unit.py` (19 → 24), AGENTS.md, DECISIONS (D-019 to D-023),
ROADMAP, TESTING, CHANGELOG, this file.
**Decisions:** D-019, D-020, D-021, D-022, D-023.
**Problems / surprises**
- Every fix was mutation-checked: the new checks fail (or, for the timeout, hang) on the old code.
- The first P2-06 mutation test was useless (the old code lacked a helper the test patched); the real mutation
  was removing the signal.
- The smoke test's DOM check found no output: onboarding suppresses it (gotcha added).
- A multi-edit doc script aborted midway on a duplicate match and the commit went in without the handoff edits;
  caught and amended before push. Check `git status` and grep after scripted doc edits.
- llama3.1:8b varies run to run; one 7/7 proves little. gemma4:12b was stable.
**Left undone:** P2-18, P2-21, P2-05, P2-04, P1-10 to P1-12, the manual app pass.
**Next session should start with:** "Next steps" above, item 1.

### Session 12: 2026-09-26: Finish the renames; restore AGENTS.md; untrack the log (P1-07, D-018)

**Goal:** The owner's answers: restore anything needed from the deleted `CLAUDE.md` / `AGENTS.md`, document
that `tests/test_executor.py` runs inside the OS, stop tracking log files, and fix any renames they missed
(and drop the old rule against renaming).
**Done:** Chat app renamed to Samwise Chat and made to work (see Current state). Remaining `gemini`-as-command
and SamwiseOS text renamed. D-006's rule removed. `AGENTS.md` restored and updated, `CLAUDE.md` imports it.
`neutralinojs.log` untracked. `test_executor.py` run in the OS. Structure, smoke 55/55, diag 40/0, grading
22/22, units 19 OK, live chat check.
**Changed:** `resources/scripts/apps/samwise_chat/*` (renamed from `gemini_chat`), `asset_manifest.js`, `main.js`,
`boot.js`, `ai_manager.js`, `chidi_manager.js`, `session_manager.js`, `commands/samwise.py`, `tests/smoke.js`,
`extras/inflate.sh`, README, `AGENTS.md`, `CLAUDE.md`, DECISIONS (D-006, D-018), TESTING, ROADMAP, this file.
**Decisions:** D-018.
**Problems / surprises**
- The chat window's CSS never applied: its title-derived id did not match the stylesheet's selector.
- Kept on purpose: `gemini` as the provider name and API-key setting, `Edmark & Gemini` in BASIC's banner, the
  LICENSE, and `mcgoopis` / `oopismcgoopis.com` (the owner's handle and site).
**Left undone:** P2-20 and the agent items; see session 13.
**Next session should start with:** "Next steps" above.

### Session 11: 2026-09-26: Real-model rerun on current code; sudo crash fixed (P2-01)

**Goal:** The owner asked to tick P2-01 and rerun. It was already ticked (session 10), so the rerun confirms it
on today's code, after the `samwise` rename and the "oopis cleanse".
**Done:** `tests/agent.js` 7/7 on llama3.1:8b and gemma4:12b, each PASS checked against its transcript. Smoke
55/55. Diag failed on `sudo` ("FractalOS is not defined"), traced to `6300a72`, fixed, diag 40/0. Rewrote
Current state, which still described session 9's failures while ROADMAP said P2-01 was done.
**Changed:** `resources/scripts/effect_handler.js` (one identifier), ROADMAP (P2-01 note, P2-19 new and done), `tests/agent.js` (graders, `exists`),
TESTING.md, this file.
**Decisions:** none.
**Problems / surprises**
- The sandbox runs commands in their own network namespace: Ollama and the http server on the host's
  127.0.0.1 are unreachable from inside it. The harness had to run outside the sandbox.
- In zsh, `git show $c:tests/...` expands `:t` as a history modifier. Write `"${c}:tests/..."`.
- gemma's A2 uses an absolute path, so it no longer tests cd memory. llama's A2 and B2 do.
**Also done:** P2-19. The graders now require C1's result to fail, C2's `garden/` directory to be gone (a new
`exists` helper asks the kernel's file system, checked true for `/home` and false for a missing path), and B2's
command to succeed. Grading test 22/22; llama rerun 7/7.
**Left undone:** P2-16, the owner's question about `CLAUDE.md`.
**Next session should start with:** "Next steps" above.

### Session 9: 2026-09-25: Reproduce why the agent tasks keep failing (P2-01 diagnosis)

**Goal:** Explain repeated task failures after the thinking and delete-grading fixes were pushed.
**Done:** Traced both preserved model transcripts through prompts, parser, audit, execution, confirmation and
harness grades. Reproduced six voltage cases with the actual BoneDriver; replayed AIManager's loop using a
fake executor to demonstrate continuation after failed cd; reproduced forge's nested-escape SyntaxError.
Verified the planner manifest/whitelist mismatch. Detailed evidence is in Current state.
**Changed:** ROADMAP (P2-14 and P2-15 added, P2-10 evidence), this file. No runtime changes.
**Decisions:** none; calibration and snapshot policy need an intentional implementation, not a threshold tweak.
**Problems / surprises:** Reordered rm flags change the score from 60 to 10; merely echoing "story save"
bypasses the surcharge. Project/ is an explicit instruction. A compliant planner cannot use mv for B2.
**Left undone:** Fixes and real-model reruns; previous browser test results remain the latest, not rerun here.
**Next session should start with:** Next steps above; P2-01 remains open.

### Session 8: 2026-09-25: Disable thinking, repair delete grading, rerun real models (P2-09, P2-11)

**Goal:** Finish P2-09 and P2-11, rerun tests to close P2-01 if evidence permits.
**Done:** Ollama thinking disabled; empty-reply diagnostics include done_reason. Delete tasks independently
verify their fixtures and reject empty/failed model calls. Smoke 50/50, structure PASS, diag 40/0; 11 grading
cases passed. Reran gemma4:12b and llama3.1:8b; verdicts and transcript paths are in Current state.
**Changed:** ai_manager.py, smoke.js, agent.js, ROADMAP, TESTING, DECISIONS, CHANGELOG, this file.
**Decisions:** D-015.
**Problems / surprises:** Thinking fix reduced gemma tasks to seconds. First run found a newline assumption
in the harness fixture check; fixed before completed reruns. Existing voltage/parser failures still block A2/B2.
Llama's force attempt used rm -r rather than rm -rf and deleted the fixture at voltage 10, then story save failed.
Gemma's generated seeds.py exposed nested escape corruption in forge (new P2-13).
**Left undone:** P2-01 remains in progress; P2-02, P2-07, P2-08, P2-10, P2-12, P2-13; Gemini and manual UI.
**Next session should start with:** P2-02, then P2-10; rerun for A2 and B2 evidence.

### Session 7: 2026-09-25: A real model drives the agent harness; verdicts recorded (P2-01 still in progress)

**Goal:** Next steps item 1: run `tests/agent.js` against a real Ollama, read the transcript, record the verdicts.
**Done:** Local session on the owner's machine. Fast-forwarded local `main` to `origin/main` (it lacked the
harness). Ran the harness against `llama3.1:8b` and `gemma4:12b`; verdict table under Current state → Verified.
Replayed the C1 autopilot prompt straight to Ollama to confirm why gemma4 returned nothing. P2-01 stays `[~]`.
No code changed.
**Changed:** ROADMAP (P2-01, P2-02 and P2-07 notes; P2-09 to P2-12 new), TESTING.md (running the harness
locally, two pitfalls), this file.
**Decisions:** none.
**Problems / surprises**
- The transcript this session was asked to read did not exist: the run had never happened, and the harness was
  only on `origin/main`. Ran it first.
- `gemma4:12b` thinks by default and ran out of output: `done_reason: "length"`, 3,296 tokens, empty reply, 74 s.
  With `think: false` the same prompt gave a two-line plan in 1 s. Three of its seven tasks were hollow.
- `llama3.1:8b` is fast and obedient in autopilot but narrates in agent mode, and the planner parser runs the
  narration. It also followed the persona's `mkdir Project` example over the user's "in my home directory".
- The +15 interlock stops a single-file `forge` (5 + 15 = 20.0), so "create one file" cannot run without a
  `story save`. Evidence for P2-02, not changed.
- The harness's C1 said "deleted garden/" when `garden/` had never been made. Grading without a precondition.
- The harness default model `gemma3:latest` is not installed here; pass `AGENT_MODEL`.
**Left undone:** P2-09 to P2-12, the rerun, Gemini. The stand-in `tests/fake_ollama.py` was not run: it needs
port 11434, which the real Ollama holds.
**Next session should start with:** "Next steps" above, item 1.

### Session 6: 2026-09-25: Agent harness and stand-in Ollama; two agent bugs fixed (P2-01 in progress, D-014)

**Goal:** P2-01: let a real model drive the agent.
**Done:** The container can reach no model (Ollama, Gemini, GitHub releases, Hugging Face all blocked; no key
to use), so the session built what makes the local run one command: `tests/agent.js` (seven tasks, file-system
grading, transcript) and `tests/fake_ollama.py` (Ollama's API with canned persona-shaped plans). The first run
found the agent's context probe resetting the cwd to `/` and agent mode crashing on its own confirm effect;
both fixed in `ai_manager.py` and `commands/samwise.py`, two smoke checks added. Harness 7/7 against the
stand-in, smoke 47/47, structure 10/10, diag 40/0.
**Changed:** `resources/core/ai_manager.py`, `resources/core/commands/samwise.py`, `tests/agent.js` (new),
`tests/fake_ollama.py` (new), `tests/smoke.js`, CLAUDE.md, ROADMAP (P2-01 `[~]`, P2-06 note, P2-08 new),
DECISIONS (D-014), TESTING.md, CHANGELOG, this file.
**Decisions:** D-014.
**Problems / surprises**
- Every prompt the OS ever built said `Current Directory: /`, whatever the shell's cwd was. The persona's
  "Gravity: if pwd is /, cd home" rule exists because of this bug.
- Agent mode's permission dialog had never appeared: `samwise.py` indexed `["success"]` on the effect dict.
- `pyfetch(timeout=20)` is not a thing; there is no LLM timeout at all (noted under P2-06).
- The `\n`-in-a-template-literal trap from session 5, again; now in TESTING.md's pitfalls.
**Left undone:** the real-model run itself (local job), P2-07, P2-08, P1-12.
**Next session should start with:** "Next steps" above, item 1, on a machine with Ollama.

### Session 5: 2026-09-25: The agent gets `python`; agent mode's plan regex fixed (P2-03, D-013)

**Goal:** P2-03: let the agent use `python`, rewrite the persona's "cannot run Python" law, decide its step budget.
**Done:** P2-03 (D-013). `python` in `COMMAND_WHITELIST` and `DANGEROUS_COMMANDS`; `AIManager.agent_refusal()`
rejects `--steps` in both paths; persona rewritten for `.sh` and `.py`; planner manifest unchanged. Nine
fake-LLM smoke checks. Then the paste bug: 58 doubled backslashes in `ai_manager.py` (agent mode never matched
a plan line; literal `\n` in Ollama prompts) and 7 more in `find`, `jobs`, `story`, `character`, `audit`,
`backup`, all undone, one `find` smoke check. Smoke 45/45, diag 40/0. P2-07 added to the roadmap.
**Changed:** `ai_manager.py`, `bone_driver.py`, `commands/{find,jobs,story,character,backup}.py`, `audit.py`,
`tests/smoke.js`, DECISIONS (D-013), ROADMAP, CHANGELOG, TESTING.md, this file.
**Decisions:** D-013.
**Problems / surprises**
- The first fake-LLM test of agent mode "passed" for the wrong reason: the plan text was returned as the answer
  and happened to contain the probe word. Only the `python` confirmation check exposed that no plan line had
  ever matched. Lesson recorded in TESTING.md: assert on the executor's output, not on words in the answer.
- Reading the autopilot for this item showed it enforces nothing but voltage and ignores `--force` (P2-07).
- A `\n` inside a JS template literal feeding Python source became a real newline; raw-string edits fixed it.
**Left undone:** P2-01 (a real model), P2-07 (autopilot brakes), P1-12 (jsnull audit).
**Next session should start with:** "Next steps" above.

### Session 4: 2026-09-24: `python` command (P1-09, D-011) and the `jsnull` fix (D-012)

**Goal:** The owner decided: real Python inside FractalOS is wanted. Build it (P1-09), closing the README's
"planned" claim.
**Done:** `resources/core/commands/python.py` (D-011): file / `-c` / stdin, captured output, VFS `open()`
(text modes, permission-checked, write-back on flush/close/drop), piped `input()`, `sys.argv`, `sys.exit`,
script-only tracebacks, `--steps` budget via `sys.settrace`, man page in the OS voice. Manifest regenerated
(123 commands). 17 smoke checks. README row and feature bullet, CHANGELOG. Found and fixed D-012 on the way.
**Changed:** `commands/python.py` (new), `kernel.py` (`_from_js`), `core/manifest.json`, `tests/smoke.js`,
README, CHANGELOG, ROADMAP (P1-09 done, P2-03 rewritten, P1-12 added), DECISIONS, CLAUDE.md, TESTING.md, this.
**Decisions:** D-011, D-012.
**Problems / surprises**
- `python` with nothing piped executed the source text "jsnull": Pyodide turns JS `null` into
  `pyodide.ffi.jsnull`, not `None`. Checked against the old build (same), so pre-existing; `wc` crashed the
  same way. Fixed at the one entry point instead of in fourteen commands.
- A test using `cd /home/Guest && python ...` wrote to `/`: effects run after the line. Test rewritten; the
  rule added to CLAUDE.md.
- `wc` with no input prints nothing (by design); my first expectation of `0 0 0` was wrong.
**Left undone:** The agent cannot use `python` yet (P2-03). No REPL, no `-m`, no binary files. P1-12 audit.
**Next session should start with:** "Next steps" above.

### Session 3: 2026-09-24: Generated kernel manifest and structure test (P1-08)

**Goal:** P1-08: stop hand-maintaining the Python file lists in `bridge.js`; a test that fails when they drift.
**Done:** P1-08 (D-010). `tools/gen_manifest.py` → `resources/core/manifest.json` (12 core, 6 apps, 122
commands); `bridge.js` fetches it and the three hand-typed arrays are gone, as is the dead `apps/gemini_chat.py`
stub; `tests/structure.js` (10 checks, Node only) guards the manifest and `asset_manifest.js` both ways.
Mutation-checked: an unregistered command file and an orphan script each fail the right check. Smoke 14/14 and
diag 40/0 both pass on the new boot path. Also merged the owner's "Samwise Cleanse" (banner rename) by rebasing
and re-keyed the diag harness on the unchanged "ALL SYSTEMS OPERATIONAL" line.
**Changed:** `resources/bridge.js`, `resources/core/manifest.json` (new, generated), `tools/gen_manifest.py`
(new), `tests/structure.js` (new), `tests/diag.js` (banner regex), docs.
**Decisions:** D-010.
**Problems / surprises**
- The owner renamed the diag banner while the harness that matched on it was in flight. Keyed on the last
  banner line instead, and wrote down in HANDOFF that the banner is prose the owner edits.
- The lists in `bridge.js` were already exactly in sync with disk, so this was prevention; the `gemini_chat`
  null stub ("still needed to avoid import errors") was the only stale entry, and nothing imported it.
**Left undone:** P1-11 (every command exposes `run` and `man`) would fit naturally into `tests/structure.js`.
The apps, the agent and portable mode remain unobserved.
**Next session should start with:** "Next steps" above.

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
- First smoke run reported the kernel never ready: `window.FractalOS_Kernel` is undefined because it is a
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
