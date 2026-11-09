#!/usr/bin/env python3
"""Check the project docs for the mistakes that make a handoff lie (P10-02).

    python3 tools/check_docs.py        # from anywhere; tests/structure.js runs it too

Adapted from the Manifold template's checker (`../the-manifold/tools/check_docs.py`, 2026-11-08), with two
additions for the failures this repo has actually had: session-log entries out of order, and Layout rows that
name several paths.

Errors (exit 1):
  - a {{placeholder}} left in a doc
  - a roadmap ID used twice, filed under the wrong phase, or with an unknown checkbox
  - a decision number used twice or out of order, or superseded by one that does not exist or comes earlier
  - an open question (Q-NNN) defined twice
  - a held tension (T-NNN) used twice, out of order, or referenced but not defined
  - a roadmap ID, decision number, question or tension mentioned in a doc that does not exist
  - two session-log entries with the same number (HANDOFF and docs/archive/ together), or entries that are not
    newest first
  - a relative link, or a path in AGENTS.md's Layout table, that points at nothing
  - an invisible or bidirectional control character in a document
Warnings (exit 0):
  - HANDOFF's "Last updated" is missing, or older than its newest session-log entry
  - HANDOFF's session log or "Current state" has outgrown the limits below (time to archive)

Standard library only. HTML comments and fenced code blocks are ignored, so examples can live in them.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = [
    "AGENTS.md", "CLAUDE.md", "README.md",
    "docs/README.md", "docs/ROADMAP.md", "docs/HANDOFF.md", "docs/ARCHITECTURE.md", "docs/DECISIONS.md",
    "docs/TESTING.md", "docs/SECURITY.md", "docs/CHANGELOG.md", "docs/CONTRIBUTING.md",
]
# Keep in step with AGENTS.md (end of session, step 3), HANDOFF's header and docs/archive/README.md.
LOG_LIMIT = 10
CURRENT_STATE_LINES = 80

ITEM_RE = re.compile(r"\bP(\d+)-(\d+)\b")
DECISION_RE = re.compile(r"\bD-(\d{3})\b")
QUESTION_RE = re.compile(r"\bQ-(\d{3})\b")
TENSION_RE = re.compile(r"\bT-(\d{3})\b")
INVISIBLE_RE = re.compile(r"[᠎​-‏‪-‮⁠-⁯﻿]")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
LINK_RE = re.compile(r"\]\(([^)\s]+)\)|\b(?:href|src)=\"([^\"]+)\"")
SESSION_RE = re.compile(r"^### Session (\d+)\b([^\n]*)", flags=re.M)

errors, warnings = [], []


def blank(match):
    """Replace a match with as many newlines as it had, so line numbers stay right."""
    return "\n" * match.group(0).count("\n")


def read(path):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", blank, text, flags=re.S)
    return re.sub(r"^```.*?^```", blank, text, flags=re.S | re.M)


def where(path, text, pos):
    return f"{path.relative_to(ROOT)}:{text.count(chr(10), 0, pos) + 1}"


def section(text, heading):
    m = re.search(rf"^## {heading}\b.*?(?=^## |\Z)", text, flags=re.M | re.S)
    return (m.group(0), m.start()) if m else ("", 0)


def main():
    docs = [ROOT / d for d in DOCS if (ROOT / d).is_file()]
    archive = ROOT / "docs" / "archive"
    if archive.is_dir():
        docs += sorted(p for p in archive.iterdir() if p.suffix in (".md", ".html") and not p.name.startswith("_"))
    texts = {p: read(p) for p in docs}

    for path, text in texts.items():
        for m in re.finditer(r"\{\{[^}]*\}\}", text):
            errors.append(f"{where(path, text, m.start())}: placeholder left: {m.group(0)[:60]}")

    roadmap = ROOT / "docs" / "ROADMAP.md"
    items = set()
    if roadmap not in texts:
        errors.append("no docs/ROADMAP.md")
    else:
        text, phase = texts[roadmap], None
        for m in re.finditer(r"^## Phase (\d+)|^- \[(.)\] (P(\d+)-(\d+))\b", text, flags=re.M):
            if m.group(1):
                phase = m.group(1)
                continue
            box, item, item_phase = m.group(2), m.group(3), m.group(4)
            if item in items:
                errors.append(f"{where(roadmap, text, m.start())}: {item} is used twice")
            items.add(item)
            if box not in " x~-":
                errors.append(f"{where(roadmap, text, m.start())}: {item} has checkbox [{box}]; use [ ], [~], [x] or [-]")
            if phase is not None and item_phase != phase:
                errors.append(f"{where(roadmap, text, m.start())}: {item} is filed under Phase {phase}")
        # Archived phases keep their IDs reserved.
        for path, text in texts.items():
            if path.parent == archive:
                items.update(m.group(1) for m in re.finditer(r"^- \[.\] (P\d+-\d+)\b", text, flags=re.M))

    decisions_path = ROOT / "docs" / "DECISIONS.md"
    decisions, supersessions, questions, tensions = set(), [], set(), set()
    if decisions_path in texts:
        text, last = texts[decisions_path], 0
        for m in re.finditer(r"^## D-(\d{3})\b([^\n]*)", text, flags=re.M):
            number = int(m.group(1))
            if f"D-{m.group(1)}" in decisions:
                errors.append(f"{where(decisions_path, text, m.start())}: D-{m.group(1)} is used twice")
            elif number < last:
                errors.append(f"{where(decisions_path, text, m.start())}: D-{m.group(1)} comes after D-{last:03d}")
            decisions.add(f"D-{m.group(1)}")
            last = max(last, number)
            by = re.search(r"superseded by D-(\d{3})", m.group(2))
            if by:
                supersessions.append((number, int(by.group(1)), m.start()))
        for number, by, pos in supersessions:
            if f"D-{by:03d}" in decisions and by <= number:
                errors.append(f"{where(decisions_path, text, pos)}: D-{number:03d} is superseded by an earlier "
                              f"decision, D-{by:03d}")
        for m in re.finditer(r"^- \*\*Q-(\d{3})\*\*", text, flags=re.M):
            if f"Q-{m.group(1)}" in questions:
                errors.append(f"{where(decisions_path, text, m.start())}: Q-{m.group(1)} is used twice")
            questions.add(f"Q-{m.group(1)}")
        last_t = 0
        for m in re.finditer(r"^### T-(\d{3})\b", text, flags=re.M):
            number = int(m.group(1))
            if f"T-{m.group(1)}" in tensions:
                errors.append(f"{where(decisions_path, text, m.start())}: T-{m.group(1)} is used twice")
            elif number < last_t:
                errors.append(f"{where(decisions_path, text, m.start())}: T-{m.group(1)} comes after T-{last_t:03d}")
            tensions.add(f"T-{m.group(1)}")
            last_t = max(last_t, number)
    else:
        errors.append("no docs/DECISIONS.md")

    for path, text in texts.items():
        for m in INVISIBLE_RE.finditer(text):
            errors.append(f"{where(path, text, m.start())}: invisible or bidirectional control character "
                          f"U+{ord(m.group(0)):04X}")
        for m in ITEM_RE.finditer(text):
            if items and m.group(0) not in items:
                errors.append(f"{where(path, text, m.start())}: {m.group(0)} is not in the roadmap")
        if decisions_path in texts:
            for m in DECISION_RE.finditer(text):
                if m.group(0) not in decisions:
                    errors.append(f"{where(path, text, m.start())}: {m.group(0)} is not in DECISIONS.md")
            for m in QUESTION_RE.finditer(text):
                if m.group(0) not in questions:
                    errors.append(f"{where(path, text, m.start())}: {m.group(0)} is not in DECISIONS.md's open questions")
            for m in TENSION_RE.finditer(text):
                if m.group(0) not in tensions:
                    errors.append(f"{where(path, text, m.start())}: {m.group(0)} is not in DECISIONS.md's held tensions")
        for m in LINK_RE.finditer(text):
            target = (m.group(1) or m.group(2)).split("#")[0]
            if not target or re.match(r"[a-z][a-z0-9+.-]*:", target):
                continue
            if not (path.parent / target).exists():
                errors.append(f"{where(path, text, m.start())}: link to {target}, which does not exist")

    agents = ROOT / "AGENTS.md"
    if agents in texts:
        layout, offset = section(texts[agents], "Layout")
        for row in re.finditer(r"^\| (.+?) \|", layout, flags=re.M):
            # Every backticked path with a slash in the first cell; bare names like `groups.py` are shorthand.
            for m in re.finditer(r"`([^`]+)`", row.group(1)):
                if "/" in m.group(1) and not (ROOT / m.group(1)).exists():
                    errors.append(f"{where(agents, texts[agents], offset + row.start())}: Layout lists "
                                  f"{m.group(1)}, which does not exist")

    handoff = ROOT / "docs" / "HANDOFF.md"
    if handoff in texts:
        text = texts[handoff]
        sessions = [(int(m.group(1)), (DATE_RE.search(m.group(2)) or [None])[0]) for m in SESSION_RE.finditer(text)]
        seen = {}
        for path in [handoff] + sorted(p for p in texts if p.parent == archive):
            previous = None
            for m in SESSION_RE.finditer(texts[path]):
                number = int(m.group(1))
                if number in seen:
                    errors.append(f"{where(path, texts[path], m.start())}: a second entry for Session {number} "
                                  f"(the first is in {seen[number]})")
                seen.setdefault(number, path.relative_to(ROOT))
                if previous is not None and number >= previous:
                    errors.append(f"{where(path, texts[path], m.start())}: Session {number} follows Session "
                                  f"{previous}; the log is newest first")
                previous = number
        archived = [n for n, p in seen.items() if p.parent == archive.relative_to(ROOT)]
        if sessions and archived and min(n for n, _ in sessions) < max(archived):
            errors.append(f"docs/HANDOFF.md: holds Session {min(n for n, _ in sessions)}, older than archived "
                          f"Session {max(archived)}; archive the oldest entries, not the newest")
        updated = re.search(r"Last updated:\s*(\d{4}-\d{2}-\d{2})", text)
        newest = max((d for _, d in sessions if d), default=None)
        if not updated:
            warnings.append("docs/HANDOFF.md: no 'Last updated: YYYY-MM-DD' line in Current state")
        elif newest and updated.group(1) < newest:
            warnings.append(f"docs/HANDOFF.md: Current state was last updated {updated.group(1)}, "
                            f"but the session log has an entry from {newest}")
        if len(sessions) > LOG_LIMIT:
            warnings.append(f"docs/HANDOFF.md: {len(sessions)} session-log entries; move all but the newest "
                            f"{LOG_LIMIT} to docs/archive/")
        current, _ = section(text, "Current state")
        if current.count("\n") > CURRENT_STATE_LINES:
            warnings.append(f"docs/HANDOFF.md: Current state is {current.count(chr(10))} lines (limit "
                            f"{CURRENT_STATE_LINES}); move history to the session log")
    else:
        errors.append("no docs/HANDOFF.md")

    for line in errors:
        print(f"ERROR {line}")
    for line in warnings:
        print(f"WARN  {line}")
    print(f"{len(errors)} error(s), {len(warnings)} warning(s) in {len(texts)} file(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
