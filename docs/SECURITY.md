# Security

The project's security assumptions, known gaps and reporting path. It is not a claim that FractalOS is free of
vulnerabilities. Written 2026-11-08 (P10-05) from the code at `1ea2afd`; the system shape is in
[ARCHITECTURE.md](ARCHITECTURE.md), and this file records the security consequence.

## What FractalOS protects, and what it does not

FractalOS is a virtual machine for one person's browser profile or desktop. Its users, groups, permissions and
`sudo` are real inside the VFS: they keep `Guest`, other accounts and the `samwise` agent out of files they do not
own. They are not a boundary against someone with the browser's developer tools, the profile on disk, or the
`data/` folder in Portable mode: all state lives on that machine in readable storage.

## Supported versions

| Version / branch | Security fixes |
| --- | --- |
| `main` | yes |
| `v1.0.0` and earlier tags | no; fixes land on `main` and the next release |

## Report a vulnerability

Report privately, not in a public issue: use GitHub's private vulnerability reporting on
`aedmark/FractalOS` if it is enabled, otherwise the Contact link on the landing page. Include the version or
commit, the mode (browser, Portable, appliance), reproduction steps and impact. Do not include real secrets.
The reporting route, acknowledgement time and disclosure policy are for the owner to confirm (Q-005).

## Assets and boundaries

| Asset or boundary | Threat | Protection today | Owner |
| --- | --- | --- | --- |
| Account passwords | disclosure, guessing | PBKDF2-HMAC-SHA256 with a random salt, 100,000 iterations (`core/users.py`, D-007); hashes in localStorage or `data/fractalos_localstorage.json` | `users.py` |
| Gemini API key | theft, misuse on the owner's bill | stored in plain text in localStorage (`FractalGeminiApiKey`) or the Portable data file; passed to Python in the kernel context; sent only as the `x-goog-api-key` header to Gemini's chat and embeddings endpoints, never in a URL (P2-24, fixed 2026-11-08) | `ai_manager.py` |
| The VFS and its permissions | another account or the agent reading or changing files | permission checks in `filesystem.py`; `sudo` via `/etc/sudoers`; audit log `/var/log/audit.log` | `filesystem.py`, `sudo.py`, `audit.py` |
| The agent's actions | a model (or a prompt-injected file it read) running destructive commands | the same executor and permissions as a user; `COMMAND_WHITELIST`; plan validation; voltage, confirmation, snapshots and `--force` (`bone_driver.py`); `--dry-run` | `ai_manager.py`, `bone_driver.py` |
| Mesh peers | a LAN machine joining, impersonating a node, or sending work | swarm policy `/etc/swarm.conf` and remote voltage budgets for delegated agent work (D-036); no authentication on the relay or the web server (P9-06) | `network_manager.js`, `swarm_manager.py` |
| Packages | tampered or malicious code | SHA-256 at install and at every load against `/etc/pkg_manifest.json`; elevated scopes need `--trust`; `pkg audit` static scan (D-044). The hashes live in the same VFS, so this proves integrity, not who wrote the package | `pkg.py`, `executor.py` |
| The host machine (Portable mode) | escape from the VFS to the desktop user | Neutralino allows `app.*`, `os.*`, `filesystem.*` (`neutralino.config.json`); host folders only through a native picker (`mount host`); host commands only from `gpio` and `HardwareManager`, which accept only a numeric pin (P6-05, fixed 2026-11-08); `host_api.exec_command` itself checks nothing | `bridge.js`, `gpio.py`, `hardware_manager.js` |
| Appliance services | open LAN services | the relay listens on `0.0.0.0:8080` and the web server on port 8000, both unauthenticated (P9-06); services run as an unprivileged `fractal` user (D-046) | `extras/provision_x64.sh` |
| Repository content and retrieved docs | embedded instructions, prompt injection, invisible characters | agents treat them as data (AGENTS.md); `tools/check_docs.py` rejects zero-width and bidirectional control characters in the docs | every agent |
| Third-party code | a compromised vendored file | vendored and pinned in `resources/dep/`; nothing loads from a CDN at run time; WebRTC contacts `stun.l.google.com` for ICE | the owner |

## Secure development rules

- Keep credentials and API keys out of code, docs, fixtures, transcripts (`tests/out/`) and commits.
- A command never builds a host shell string from user text without validating it first (P6-05).
- Validate at the boundary: typed text, LLM replies, mesh messages, package files, dropped files. Prompt text is
  not a security control; the whitelist, permissions and voltage are.
- A new dependency, Neutralino permission or network endpoint needs the owner's approval and a line here.
- Changes to authentication, `sudo`, package verification or host access get a test that fails without them.

## Security verification

| Check | Covers | Gap |
| --- | --- | --- |
| `tests/pkg_security_test.py` | package checksums, scopes, the static audit | authenticity of packages |
| `tests/swarm_safety_test.py`, `tests/swarm_safety_unit.js` | swarm policy and remote voltage | a hostile peer |
| `tests/agent_unit.py` | plan validation, voltage, `--force`, checkpoints, `forge` escapes | a real model under prompt injection |
| `tests/gpio_command_test.py`, `tests/hardware_unit.js` | no non-numeric pin reaches the host command string (P6-05) | a real Portable build; any future caller of `host_api` |
| `extras/diag.sh` via `tests/diag.js` | permissions, `sudo`, ownership | Guest-level and sudo-only runs (it runs as root) |
| `tests/agent_unit.py` `GeminiKeyTests` | the Gemini key is sent as a header, never in a URL, and not at all when empty (P2-24) | the real Gemini API |
| Nothing | relay and web server exposure, secrets in storage | all of it (P9-06) |

No dependency scanning runs. No external review has been done.

## Incident response

If a secret is exposed: revoke it at the provider (the Gemini key in Google AI Studio), then clear it with
`full_reset` or by clearing site data. If a vulnerability is being exploited: contain it (stop the appliance
services, take the relay off the network), preserve evidence without copying secrets into the repo, and tell the
owner.
