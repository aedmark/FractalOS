# Testing: how to check FractalOS actually works

`SESSION_HANDOFF` for this project is `HANDOFF.md`: the dated log of what happened. This file is the standing
reference for how to run the checks again, what each one proves, and the traps already hit so a new session
does not re-discover them. `ROADMAP.md` says what is planned; `DECISIONS.md` (D-008) says why the tests look
the way they do.

There are four layers. The first three are automated.

| Layer | What | Proves | Runs in |
| --- | --- | --- | --- |
| Structure | `tests/structure.js` | Every Python file is in `core/manifest.json`; every script and stylesheet is in `asset_manifest.js`; nothing listed is missing | a second, Node only |
| Smoke | `tests/smoke.js` | Pyodide boots, kernel comes up, accounts and hashing work, the executor runs commands | ~40 s, headless Chromium |
| In-OS suite | `tests/diag.js` running `extras/diag.sh` | 40+ phases of command behaviour, permissions, sudo, jobs, text tools, archives, links, scripting | ~2 min, headless Chromium, inside the OS as root |
| Agent | `tests/agent.js` (+ `tests/fake_ollama.py`) | The `gemini` agent plans and acts against a real Ollama: seven tasks graded on the file system, transcript recorded | ~1 min with the stand-in, model-bound with Ollama; needs a machine with a model |
| Manual | CONTRIBUTING.md checklist | UI, apps, sounds, portable mode | a person |

## The structure test

```bash
node tests/structure.js
python3 tools/gen_manifest.py --check   # the manifest half only, for machines without Node
```

Ten checks, no browser. It exists because both registration lists fail silently (D-003, D-010): a Python file
not in `resources/core/manifest.json` is never copied into Pyodide, and a `.js` not in `asset_manifest.js`
never loads. Mutation-checked on 2026-09-24: an unregistered `commands/zz.py` fails the manifest check and
`--check`; an orphan `scripts/zz.js` fails the asset check. Fix the first with `python3 tools/gen_manifest.py`;
fix the second by adding the file to `asset_manifest.js` in the right place (order matters there, so the test
does not try to enforce it).

## The smoke test

### Requirements

- Node 18+ (developed on 22).
- Playwright with a Chromium. Either `npm i -g playwright && npx playwright install chromium`, or point the
  script at an existing browser with `CHROME=/path/to/chrome`.
- A web server on `resources/`. The app cannot run from `file://` (D-003).

### Run

```bash
cd resources && python3 -m http.server 8000 &       # or ./start_server.sh
node tests/smoke.js http://127.0.0.1:8000/index.html
```

If Playwright is installed globally rather than in the repo, tell Node where it is:
`NODE_PATH=$(npm root -g) node tests/smoke.js ...`.

Exit code 0 means every check passed. The output ends with a summary line, `PASS n/n` or `FAIL k of n`, and
each failed check prints what it expected and what it got. Console errors and failed requests from the page are
printed at the end either way; the `AudioContext was not allowed to start` warning is normal in headless mode.

### What it does, in order

1. Opens the page in a fresh browser context (no real profile, no shared IndexedDB or localStorage, D-008).
2. Waits up to 120 s for `OopisOS_Kernel.isReady` (bare name: `OopisOS_Kernel` is a top-level `const`, not a
   `window` property). Boot is 5 to 15 s on a laptop, longer the first time the wasm is compiled.
3. Runs Python inside the kernel to report `sys.version`, `pyodide.__version__` and `cryptography.__version__`
   and to derive a PBKDF2 key. This is the check that the vendored wheels match the runtime (D-004, D-007).
4. Calls `users.first_time_setup("gordon", "hunter2", "rootpw")` through `OopisOS_Kernel.syscall`, then
   `verify_password` with the right and the wrong password. Expects `true` then `false`.
5. Runs shell commands through `CommandExecutor.processSingleCommand(cmd, { isInteractive: false })` and checks
   each result against an expectation: `echo hello` → `hello`; `date` succeeds; `whoami` → `Guest`; `ls -la /home`
   lists `gordon`, `Guest` and `root`; `help | head -3` starts with the banner; `mkdir /home/t` **fails** with
   "Permission denied" (Guest cannot write to `/home`); `cat /nonexistent` fails.

The commands run as `Guest` because the test never completes onboarding; the page is still on the "create your
main user account" dialog underneath. That is deliberate: it keeps the test independent of the onboarding UI.
Anything that needs a logged-in user with a home directory is a job for P1-06.

### Adding a check

`CHECKS` near the top of `tests/smoke.js` is a list of `{ cmd, expect }` where `expect` is a function of the
result object (`{ success, output }` or `{ success: false, error: { message, suggestion } }`) returning true on
pass. Keep each command independent of the others' side effects, or order them explicitly and say so in a
comment.

## The in-OS suite (`tests/diag.js` + `extras/diag.sh`)

### Run

```bash
cd resources && python3 -m http.server 8000 &
node tests/diag.js http://127.0.0.1:8000/index.html            # extras/diag.sh by default
node tests/diag.js http://127.0.0.1:8000/index.html other.sh   # any FractalOS script
```

Same requirements as the smoke test. It takes about 100 s (the script has 277 `delay` lines totalling 124 s,
some of which run in background jobs). The full transcript lands in `tests/out/diag-transcript.txt`
(gitignored). `DIAG_TIMEOUT_MS` raises the 15-minute ceiling.

### What it does

1. Boots the page and completes onboarding the way `OnboardingManager.onFinish` does: `first_time_setup`
   through the JS `UserManager`, the four localStorage keys, then a reload. After the reload it waits for the
   "loaded successfully" console line, so the terminal, session stack and storage are fully initialised.
2. Writes the script into `/home/root/` through the `filesystem.write_file` syscall, runs `login root rootpw`,
   `chmod 755`, `cd /home/root`.
3. Wraps `OutputManager.appendToOutput` to record every printed line and whether it carried the error class.
4. Runs `run /home/root/diag.sh` through `CommandExecutor.processSingleCommand`. The `execute_script` effect
   awaits every line, so the call returns when the script finishes or aborts.
5. Grades: PASS only if the script reached its closing banner ("ALL SYSTEMS OPERATIONAL"), no `CHECK_FAIL: FAILURE` line
   was printed, no line was printed with the error class, and at least as many `CHECK_FAIL: SUCCESS` lines
   appeared as there are top-level `check_fail` lines in the file (38; 40 run, because the script writes child
   scripts that call `check_fail` too).

A script line that fails aborts the whole run (`execute_script` prints `run: error on line N` in the error
class and breaks), so "reached the banner" is the strongest single signal.

### The script itself

A 1,435-line FractalOS shell script, not bash: it is run *inside* the OS by the `run` command, and the
interpreter is `executor.py`. It creates users and groups, builds files, then walks through 30+ phases (core FS
commands, group permissions, sudo, scripting and jobs, text utilities, `find` and `zip`, pager and `bc`, edge
cases, symlinks, signals, `tr`, `comm`, `binder`, `agenda`, brace expansion, `cast`, a "torture" phase, and a
`check_fail` assertion at each point that must fail). Password prompts are answered by the lines that follow a
`useradd` (`testpass` twice).

To run it by hand: boot the OS, finish onboarding, `login root`, `upload` the file (browser file picker) into
`/home/root`, `chmod 755 diag.sh`, `run diag.sh`, and read the output. Every `CHECK_FAIL: FAILURE` line is a
bug. It must run as root: Phase 1 creates users, writes under `/home/diagUser` and appends to `/etc/sudoers`.
First headless result, 2026-09-24, Pyodide 314.0.7 / Python 3.14.2: clean pass.

`extras/inflate.sh` is not a test. It fills `/home/Guest` with a demo world (docs, code, games, an archive) for
trying the tools on. It starts with `rm -r -f` of its own previous output; do not run it in a home you care about.

## The agent harness (`tests/agent.js`)

```bash
cd resources && python3 -m http.server 8000 &
ollama serve &                                   # a real model, or:
python3 tests/fake_ollama.py &                   # the stand-in (plumbing only, not a model)
AGENT_MODEL=gemma3:1b node tests/agent.js http://127.0.0.1:8000/index.html
```

Boots the OS, onboards as `gordon`, then runs seven tasks in order: three through `gemini --autopilot`
(make `garden/seeds.txt`; `cd garden` then make `tools.txt` there, which checks the cd memory; forge and run
`sum.py`), two through agent mode (a read-only question, then `mv garden/tools.txt garden/kit.txt`, which needs
the confirmation dialog: the harness answers "yes" and records it), and a delete request twice, without and with
`--force`. Each task is graded on the file system afterwards, never on the model's wording (D-014):

- **PASS / FAIL**: the file exists with three lines, `tools.txt` is in `garden/` and not in `$HOME`, `55` was
  printed, `kit.txt` exists, `garden/` survived the delete request.
- **INFO**: what a human should read. Whether the planner planned or answered directly, whether the synthesizer
  mentioned `garden`, the voltage report, and what `--force` did (today: nothing, P2-07). INFO never fails the run.

Exit code 0 means no FAIL. `tests/out/agent-transcript.md` holds every LLM call (prompt size, seconds, the raw
answer), every line the terminal printed, every confirmation, and the result JSON. **That transcript is the
deliverable of P2-01**: copy its verdicts and anything surprising into HANDOFF.

`AGENT_MODEL` is passed as `-m`; unset it to use the provider's default (`gemma3:latest`). `AGENT_PROVIDER=gemini`
with `GEMINI_API_KEY` stores the key in the OS first (written, never run: no key in the cloud). `AGENT_TIMEOUT_MS`
(default 10 min) bounds one task; a CPU model with a 2,500-character persona prompt can take a minute per call,
and `pyfetch` has no timeout at all (P2-06).

On the owner's machine (first real run, 2026-09-25) Playwright is not installed globally and `gemma3` is not
pulled. What worked: Playwright in a scratch directory, pointed at the system Chromium, and a model named
explicitly. The run takes about 40 s with `llama3.1:8b` and about 8 minutes with `gemma4:12b`. Each run
overwrites `agent-transcript.md`, so copy it to a per-model name before the next one.

```bash
cd /some/scratch && PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i playwright@1.56
NODE_PATH=/some/scratch/node_modules CHROME=/usr/bin/chromium AGENT_MODEL=llama3.1:8b node tests/agent.js
```

Read every verdict against the transcript. A FAIL can be a cascade (C1 checks for `garden/`, which only A1
creates), and a PASS can be hollow (a model that returned nothing "survived" the delete). P2-11 fixes the grading.

The stand-in `tests/fake_ollama.py` answers `/api/generate` with canned plans chosen by keywords in the request
(`seeds`, `tools.txt`, `sum.py`, `rename`, `delete`) and logs each request as a JSON line
(`--log tests/out/fake-ollama-requests.jsonl`, handy for seeing exactly what prompt the OS builds). Against it the
run is 7/7 in about a minute, which proves the harness, the CORS preflight, the request body and the `response`
field. It proves nothing about a model. Its first run found the two bugs in D-014, so it earns its keep as a
regression check for the agent loop.

## Manual checks (before a release)

The CONTRIBUTING.md checklist, made concrete:

- Browser mode in Chrome and Firefox: onboarding, login, `edit`, `paint`, `top`, `adventure`, `basic`, `gemini`
  with an Ollama running, `printscreen`, `theme`, `cinematic`, `beep` and `play` (needs a click first for audio).
- Portable mode: the Neutralino binary in the repo root, `data/` created on first run, state survives closing the
  window (the localStorage export on `windowClose`).
- Reload survives: files, users, aliases, history, the current theme.

## Known pitfalls (already hit, already fixed: don't re-discover these)

- **Thinking models return an empty reply through Ollama** (P2-09, not fixed yet). The kernel sends no `think`
  field, so `gemma4` reasons until `done_reason: "length"` and `response` is `""`. The OS reports "AI failed to
  generate a valid response structure" after a minute or more. Check with `curl .../api/generate` and look at
  `eval_count` and `done_reason` before blaming the prompt.
- **The real Ollama and `tests/fake_ollama.py` both want port 11434.** Stop one to run the other.
- **A `\n` inside a JS template literal that holds Python source is a real newline by the time Python sees it.**
  Hit twice now (sessions 5 and 6). Write `\\n` in the `.js` file. `node --check` cannot catch it; the smoke test
  aborts with `SyntaxError: unterminated string literal` inside `page.evaluate`.
- **The agent's nested `execute()` calls need `current_path`.** A context without one resets the kernel cwd to
  `/`. Any test that drives the agent from a subdirectory and asserts on relative paths depends on D-014.

- **Doubled backslashes in Python source** (`"\\n"` in a normal string, `r'\\d'` in a raw one) made agent mode
  never match a plan line and made `find` print one long line. Undone everywhere in `resources/core/` on
  2026-09-25 (D-013). A grep for `\\\\n` over `resources/core` should hit only `forge`, `printf`, `echo`, `python`
  and `bone_driver`, which document or expand escapes on purpose. If a new file shows the pattern, it was
  pasted through something that escapes.
- **The agent can be tested without a model.** Replace `kernel.ai_manager._call_llm_api` with an async fake
  that returns a fixed plan (see the agent block in `tests/smoke.js`); `perform_autopilot` and
  `perform_agentic_search` then run end to end against the real executor.

- **`cd` takes effect after the line.** `cd /home/Guest && python -c "open('x','w')"` wrote to `/x`: the
  `change_directory` effect runs when the whole line is done (D-002). In tests, give `cd` its own command.
- **No pipe means `jsnull`, not `None`, on the Python side** (D-012), now normalised in `kernel.execute_command`.
  The smoke test's bare `cat` and `wc` checks guard it. Symptom before the fix: `wc` crashed on `JsNull`,
  and `python` ran the word "jsnull".
- **`wc` with no input prints nothing**, by design (like `cat`). Do not expect `0 0 0`.

- **`su` and `logout` replace the terminal output.** `SessionManager.loadAutomaticState` restores the user's
  saved terminal state, including the output div, so reading `#output` after a script that switches users shows
  only the last user's tail (34 lines of 1,761 on the first try). `tests/diag.js` records output by wrapping
  `OutputManager.appendToOutput` instead. Any future harness that reads the DOM has the same problem.
- **`check_fail` count is 38 in the file and 40 at run time.** Two more come from child scripts the suite writes
  and `run`s. Treat the file count as a floor.
- **`beep` / `play` log "SoundManager not initialized" headlessly.** No user gesture, so no AudioContext. The
  diag harness ignores that one console error; anything else in the console is reported.
- **Completing onboarding without the UI:** replicate `OnboardingManager.onFinish` exactly (see `tests/diag.js`)
  and reload; `main.js` only takes the post-onboarding path on a fresh load. Setting the flag alone does not
  populate the users, groups and session stack.

- **`window.OopisOS_Kernel` is `undefined`.** Every top-level object in the app is a `const`, so it is a global
  but not a `window` property. `waitForFunction(() => window.OopisOS_Kernel ...)` waits forever. Use the bare
  name. Same for `CommandExecutor` and `dependencies`.
- **Guest has no home to write in during the smoke test.** `mkdir /home/gordon/t` is denied for Guest even after
  `first_time_setup` created `gordon`, because the executing user is still Guest. The test asserts the denial.
- **`pkill -f 'http.server 8000'` kills the shell that ran it** when the pattern also matches that shell's own
  command line (it does, under Claude Code's `bash -c` wrapper). `resources/stop_server.sh` has the same shape.
  Use `pkill -f '^python3 -m http.server'` or `kill` the PID you started.
- **Pyodide 314 renamed `pyodide.asm.js` to `pyodide.asm.mjs`.** A stale copy of the old file next to the new
  ones is harmless but confusing; the loader only asks for `.mjs`.
- **`loadPackage(["ssl"])` throws on Pyodide 314** ("No known package with name 'ssl'"): `ssl` is in the core
  now. `bridge.js` loads only `cryptography`. If `hashlib.pbkdf2_hmac` is ever needed, it is not there either;
  use `cryptography` (D-007).
- **The first-time setup syscall returns the whole users-and-groups blob** with hashes and salts in it. Fine
  in a test log; do not paste it into a doc as an example.
- **Comparing old and new runtimes:** `git archive <old-commit> resources | tar -x -C /tmp/old` and serve that
  on a second port; run the same smoke script against both and diff the outputs. That is how the 314 upgrade
  was accepted (identical command results). It still works for any future Pyodide bump.
- **`neutralinojs.log` in the repo root** is a committed artefact from the owner's Windows machine (2025-08-22).
  Errors in it about `.map` files are Neutralino failing to serve source maps and mean nothing.
