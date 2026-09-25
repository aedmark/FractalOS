# Session Handoff

Read this first. It is rewritten at the end of every session so the top half is always true *right now*.
The session log below it is append-only history.

Protocol: see [CLAUDE.md](../CLAUDE.md). Plan: [ROADMAP.md](../ROADMAP.md). Decisions: [DECISIONS.md](DECISIONS.md).
Tests: [TESTING.md](TESTING.md).

---

## Current state

_Last updated: 2026-09-25, session 7 (first real-model runs of the agent harness, on the owner's machine: verdicts recorded, P2-01 not ticked, four new items P2-09 to P2-12)._

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
- **The agent harness exists and the agent loop is proven end to end, minus the model** (P2-01 in progress,
  D-014). `node tests/agent.js` runs seven tasks through the autopilot and agent mode in headless Chromium,
  auto-confirms the permission dialog, grades on the file system and writes `tests/out/agent-transcript.md`.
  Against `tests/fake_ollama.py` (a stand-in that speaks Ollama's API with canned plans) it is 7/7: the browser's
  CORS preflight, the request body and the `response` field all work. Its first run found and this session fixed
  two bugs: **the agent's context probe reset the kernel cwd to `/`** (every plan was sensed and driven from the
  root; the persona's "Gravity" law was papering over it) and **agent mode crashed with `KeyError('success')`
  whenever it tried to ask permission** (the confirm effect was indexed like a result). Two smoke checks guard them.
- **A real model has driven the agent** (P2-01, still `[~]`). `tests/agent.js` against a local Ollama with
  `llama3.1:8b` and `gemma4:12b`. The autopilot ran a model's plan end to end twice (llama forged `sum.py`, ran
  it with `python`, printed 55 and saved a story chapter; gemma made `garden/seeds.txt` with a `story save`),
  agent mode's planner → executor → synthesizer answered a read-only question (gemma), and the voltage brake
  disengaged on a real `rm -rf garden` (llama). Verdict table below under **Verified**.
- **The agent has `python`** (P2-03, D-013): whitelisted, confirmed-first in agent mode, `--steps` refused in
  both paths, the BoneAmanita persona rewritten for `.py` scripts. **Default `gemini "<prompt>"` mode executes
  its plan now, which it never did before:** its plan-line regex had doubled backslashes and never matched.
  The whole of `ai_manager.py` and six other kernel files had the same paste bug (literal `\n` in Ollama
  prompts, `find` output, the audit log); all undone.
- **`python` runs real Python inside the OS** (P1-09, D-011). `python script.py [args]`, `python -c "..."`,
  or piped code, in the kernel's own CPython 3.14: output captured, `open()` on the virtual file system with
  permissions, `input()` from the pipe, `sys.argv` / `sys.exit`, tracebacks from the script's frames, and a
  2,000,000-step budget (`--steps`) so a runaway loop cannot freeze the page. Not a sandbox. The agent has it
  too (P2-03).
- **JS `null` no longer leaks into commands as `jsnull`** (D-012). `kernel.execute_command` normalises stdin;
  `wc` with no input used to crash. Pre-existing, not from the upgrade.
- **Registration lists are guarded** (P1-08, D-010). `bridge.js` fetches `resources/core/manifest.json`, which
  `tools/gen_manifest.py` writes from the directories; `tests/structure.js` fails in a second if that manifest
  or `asset_manifest.js` disagrees with the files on disk. Both harnesses (smoke, diag) pass on the new boot path.
- **Docs**: this file, `CLAUDE.md`, `ROADMAP.md`, `docs/DECISIONS.md` (D-001 to D-009), `docs/TESTING.md`,
  `tests/smoke.js`, `.gitignore`. README and CONTRIBUTING point at them.

**Verified**
- `node tests/agent.js` against a real Ollama, 2026-09-25, on the owner's machine (Chromium 153 via Playwright
  1.56, Node 22). The harness said 6 FAIL of 7 for `llama3.1:8b` and 3 FAIL of 7 for `gemma4:12b`; what actually
  happened is below. Transcripts: `tests/out/agent-transcript-llama3.1-8b.md`, `-gemma4-12b.md` (gitignored,
  local only).

  | Task | `llama3.1:8b` (1 to 14 s per call) | `gemma4:12b` (22 to 94 s per call) |
  | --- | --- | --- |
  | A1 make `garden/seeds.txt` | FAIL. Right plan in backticks, but `story begin` without `story save`: 25.1, disengaged | PASS. 3 lines, voltage 10.0, story saved |
  | A2 `cd garden`, then `tools.txt` | FAIL, cascade from A1. `cd` failed, the next line wrote `tools.txt` into `$HOME`, report said success | FAIL. Right plan (`cd garden`, `forge`), but one `forge` without `story save` is 20.0: disengaged |
  | A3 forge and run `sum.py` | FAIL by the letter. Put it in `~/Project/` (the persona's example), ran it, printed 55, saved | FAIL. Reply cut off after `2.`: thinking ran out the output budget (P2-09) |
  | B1 agent mode, read-only | FAIL. Plan wrapped in prose; parser ran `**Step` as a command and halted (P2-10) | PASS. Planned `ls`; the synthesizer said the home holds `garden` |
  | B2 agent mode, confirm `mv` | FAIL. Prose again (`We start by...`), halted before asking | FAIL. Empty reply after 94 s (P2-09) |
  | C1 autopilot, delete `garden/` | Brake held: `rm -rf` → CRITICAL, disengaged. Harness said FAIL only because `garden/` never existed (P2-11) | Hollow PASS: empty reply after 92 s, nothing ran (P2-09, P2-11) |
  | C2 same with `--force` | INFO. Disengaged; `--force` changed nothing (P2-07) | INFO. Empty reply, nothing ran |

  The `cd` memory across plan lines worked in passing: gemma's `cd garden` put `seeds.txt` in `garden/` (A1) and
  llama's `cd Project` put `sum.py` in `Project/` (A3). Never reached with a real model: task A2 itself and agent
  mode's confirmation dialog (B2). Those need P2-09 and P2-10 first.
  Also seen: the voltage audit scores `echo` as a read (0.1) even with a `>` redirect that writes a file (llama A2).
- `node tests/agent.js` against `tests/fake_ollama.py`: 7/7 (A1 seeds.txt with 3 lines, A2 tools.txt in garden/,
  A3 sum.py printed 55, B1 planner + synthesizer, B2 confirmation then kit.txt, C1 disengaged at critical voltage,
  C2 `--force` changed nothing). Before the two fixes it was 5/7 (A2 and B2 failed).
- `node tests/smoke.js`: 47/47 (two new: the context probe keeps the cwd; `gemini` passes the confirm effect).
- `node tests/structure.js`: 10/10. `node tests/diag.js`: PASS, 40/0, 106 s, after the kernel edits.
- `node tests/smoke.js`: 45/45. Nine drive the agent with a fake `_call_llm_api`: the autopilot runs a
  `python -c` plan line and refuses `--steps`; agent mode asks before `python`, halts on `--steps`, and still
  runs a read-only plan through to the synthesizer. One checks `find` prints one path per line.
- (earlier) `node tests/smoke.js`: 35/35 (17 of them exercise `python`: values, argv, piped `input()`, VFS read, write
  on drop, append in a `with`, a permission denial on `/etc/sudoers`, a traceback after partial output, exit
  status, a syntax error, the step budget, python-to-python pipe, and the no-input case); bare `cat` and `wc`
  guard D-012.
- `node tests/structure.js`: 10/10; fails as intended on an unregistered Python file and on an orphan script.
- `node tests/diag.js http://127.0.0.1:8000/index.html`: PASS, exit 0, twice in a row (Chromium 1194 via
  Playwright 1.56, Node 22). Transcript 1,761 lines.
- (earlier) `node tests/smoke.js`: 14/14 checks pass on Pyodide 314.0.7 (Chromium 1194
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
- **A real model has been observed, but P2-01 is not done.** Task A2 never ran and agent mode's confirmation was
  never reached (table above). The `cd` memory did work in passing, in gemma's A1 and llama's A3. Gemini has not been tried (no key). Only two models; each run once.
- **Thinking models get nothing back** (P2-09). No `think: false` in the Ollama request, so `gemma4` spends its
  output on hidden reasoning and returns an empty `response`. Confirmed by replaying the C1 prompt directly.
- **Agent mode chokes on chatty planners** (P2-10): any numbered prose line is taken as a command.
- **Agent mode stops after a confirmation** (P2-08): only the confirmed command runs; the rest of the plan and the
  synthesizer are dropped. Seen in task B2. Not changed.
- **The autopilot has no brakes but voltage** (P2-07): no whitelist check, `--force` unread. Found while
  doing P2-03, not changed.
- **Portable (Neutralino) mode is untested here**: no binary in the container. The config pins Neutralino 6.2.0.
- **Firefox and Safari**: untested. Pyodide 314's `pyodide.js` dynamic-imports `pyodide.asm.mjs`; that is fine
  in every evergreen browser but has only been seen in Chromium.
- **`neutralinojs.log` is still tracked** (P1-07). The owner removed `.idea/` from `main` on 2026-09-25;
  `.gitignore` lists the log but does not untrack it.

**Gotchas for the next session**
- **Two names.** The code says OopisOS (`OopisOS_Kernel`, `oopisOs*` keys, `oopisos-network`); the product is
  FractalOS. Do not rename either (D-009).
- **`cd` is an effect and applies after the line.** `cd x && cmd` runs `cmd` in the old directory. One
  command per line in tests.
- **Raw JS values can be `jsnull`.** Only stdin crosses raw today and is normalised (D-012). P1-12 audits the
  rest.
- **Registration lists.** A new JS file must be in `resources/scripts/asset_manifest.js` (hand-ordered); a new
  Python file needs `python3 tools/gen_manifest.py`. `node tests/structure.js` catches both omissions (D-010).
  `core/manifest.json` is generated: never hand-edit it, and resolve a merge conflict in it by regenerating.
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
- **The diag script's closing banner is prose the owner edits** (it went from "SamwiseOS Core Test Suite ...
  Complete" to "FractalOS Gauntlet Complete" the same day the harness was written). `tests/diag.js` keys on the
  "ALL SYSTEMS OPERATIONAL" line; if that line changes, change the regex in the harness with it.
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

1. **P2-09: send `think: false` to Ollama** and say `done_reason` when a reply is empty. Small, in
   `_call_llm_api`. Without it every thinking model on the owner's machine (`gemma4`, `qwen3`, `qwen3.5`) is
   unusable.
2. **P2-11: fix the harness's C1/C2 preconditions** so a failed A1 cannot fake a verdict, and so an empty
   model reply is its own verdict. Then P2-10 (agent mode's plan extraction).
3. **P2-01: rerun** `tests/agent.js` with `gemma4:12b` and `llama3.1:8b` (local only; recipe in TESTING.md) and
   tick P2-01 if A2 and B2 are observed working. Then P2-02 with the voltage evidence now in ROADMAP (a single
   `forge` cannot run without `story save`), P2-07 and P2-08.

## Open questions for the user

- Untrack `neutralinojs.log`? (P1-07; `.idea/` is gone)
- What does "long-term memory" mean for Milestone 1? (Q-003, P3-01)
- Should the agent whitelist converge on "anything a user can do" with voltage as the brake? (Q-001)

---

## Session log

Newest first. Copy the template for each new session.

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
both fixed in `ai_manager.py` and `commands/gemini.py`, two smoke checks added. Harness 7/7 against the
stand-in, smoke 47/47, structure 10/10, diag 40/0.
**Changed:** `resources/core/ai_manager.py`, `resources/core/commands/gemini.py`, `tests/agent.js` (new),
`tests/fake_ollama.py` (new), `tests/smoke.js`, CLAUDE.md, ROADMAP (P2-01 `[~]`, P2-06 note, P2-08 new),
DECISIONS (D-014), TESTING.md, CHANGELOG, this file.
**Decisions:** D-014.
**Problems / surprises**
- Every prompt the OS ever built said `Current Directory: /`, whatever the shell's cwd was. The persona's
  "Gravity: if pwd is /, cd home" rule exists because of this bug.
- Agent mode's permission dialog had never appeared: `gemini.py` indexed `["success"]` on the effect dict.
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
