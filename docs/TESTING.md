# Testing: how to check FractalOS actually works

`SESSION_HANDOFF` for this project is `HANDOFF.md`: the dated log of what happened. This file is the standing
reference for how to run the checks again, what each one proves, and the traps already hit so a new session
does not re-discover them. `ROADMAP.md` says what is planned; `DECISIONS.md` (D-008) says why the tests look
the way they do.

There are three layers. Only the first is automated today.

| Layer | What | Proves | Runs in |
| --- | --- | --- | --- |
| Smoke | `tests/smoke.js` | Pyodide boots, kernel comes up, accounts and hashing work, the executor runs commands | ~40 s, headless Chromium |
| In-OS suite | `extras/diag.sh` | 30+ phases of command behaviour, permissions, sudo, jobs, text tools, archives, links | minutes, inside the OS, read by a human (P1-06 automates it) |
| Manual | CONTRIBUTING.md checklist | UI, apps, sounds, portable mode | a person |

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

## The in-OS suite (`extras/diag.sh`)

A 1,435-line FractalOS shell script, not bash: it is run *inside* the OS by the `run` command, and the
interpreter is `executor.py`. It creates users and groups, builds files, then walks through 30+ phases (core FS
commands, group permissions, sudo, scripting and jobs, text utilities, `find` and `zip`, pager and `bc`, edge
cases, symlinks, signals, `tr`, `comm`, `binder`, `agenda`, brace expansion, `cast`, a "torture" phase, and a
`check_fail` assertion at each point that must fail). Password prompts are answered by the lines that follow a
`useradd` (`testpass` twice).

To run it by hand today: boot the OS, finish onboarding, `upload` the file (browser file picker) into your home
directory, `chmod 755 diag.sh`, `run diag.sh`, and read the output. Every `CHECK_FAIL: FAILURE` line is a bug.
It has not been run in this doc's lifetime; P1-06 is to drive it from the smoke harness and count the failures.

`extras/inflate.sh` is not a test. It fills `/home/Guest` with a demo world (docs, code, games, an archive) for
trying the tools on. It starts with `rm -r -f` of its own previous output; do not run it in a home you care about.

## Manual checks (before a release)

The CONTRIBUTING.md checklist, made concrete:

- Browser mode in Chrome and Firefox: onboarding, login, `edit`, `paint`, `top`, `adventure`, `basic`, `gemini`
  with an Ollama running, `printscreen`, `theme`, `cinematic`, `beep` and `play` (needs a click first for audio).
- Portable mode: the Neutralino binary in the repo root, `data/` created on first run, state survives closing the
  window (the localStorage export on `windowClose`).
- Reload survives: files, users, aliases, history, the current theme.

## Known pitfalls (already hit, already fixed: don't re-discover these)

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
