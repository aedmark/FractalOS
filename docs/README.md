# Documentation map

Which document owns each kind of fact, so each fact has one home and the others link to it. Agents start with
[AGENTS.md](../AGENTS.md); people start with the [README](../README.md).

## Audiences and ownership

| Document | Audience | Owns | Does not own |
| --- | --- | --- | --- |
| [`../README.md`](../README.md) | users and newcomers | what FractalOS is, quick start, the command table | session state, internal rules |
| [`../AGENTS.md`](../AGENTS.md) (`CLAUDE.md` imports it) | coding agents and the owner | session protocol, layout, conventions, how to run the tests | feature history, design rationale |
| [`ROADMAP.md`](ROADMAP.md) | the owner and contributors | planned, finished and dropped work with permanent `P<phase>-<nn>` IDs, bugs included | implementation detail |
| [`HANDOFF.md`](HANDOFF.md) | the next session | current state, next steps, the last ten sessions | permanent rules |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | developers | components, interfaces, invariants, boundaries, dependencies, state, failure modes, claims vs. code | history; why (that is DECISIONS) |
| [`DECISIONS.md`](DECISIONS.md) | whoever is about to change a choice | decisions (`D-NNN`), open questions (`Q-NNN`) | routine detail |
| [`TESTING.md`](TESTING.md) | anyone claiming something works | every suite: command, what it proves, pitfalls | current results (those are in HANDOFF) |
| [`SECURITY.md`](SECURITY.md) | users and developers | assets, trust boundaries, known gaps, reporting | the system shape (ARCHITECTURE) |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | human contributors | setup, adding a command, PR conventions | agent-only rules |
| [`CHANGELOG.md`](CHANGELOG.md) | users | user-visible changes per release | commit or session history |
| [`devlog.html`](devlog.html) | readers | the dev diary, first person, newest first | file names, agent detail |
| [`manual/`](manual/index.html) | readers | the long-form codex and command reference | current truth when it disagrees with the code |
| [`archive/`](archive/README.md) | anyone searching history | session logs moved out of HANDOFF | anything current |
| [`../tools/check_docs.py`](../tools/check_docs.py) | every session | that these documents agree with each other | that they agree with the code |

## Update triggers

Update a document because a fact it owns changed, not because a session ended.

| Change | Update |
| --- | --- |
| Behaviour a user would notice | CHANGELOG; README if the quick start or command table changed |
| A module, interface, dependency, data flow or invariant | ARCHITECTURE |
| A choice someone might revisit, or a reversal | DECISIONS (a reversal supersedes; it never deletes) |
| A question only the owner can answer | DECISIONS, Open questions; cite its `Q-NNN` from HANDOFF |
| A test, command, fixture or environment | TESTING |
| A secret, trust boundary, permission or exposed service | SECURITY |
| A file added, moved or deleted | AGENTS.md Layout table; `python3 tools/gen_manifest.py` for Python files |
| Work pauses, or current state changed | HANDOFF (and archive past ten entries) |
| New planned work or a bug | ROADMAP, with where it came from and the date |
| A milestone, when the owner asks | devlog |

Run `node tests/structure.js` after any of these; it runs the docs checker.
