#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""check_citation_paths.py — a committed doc may not cite a `scratchpad/` path
the repo does not contain.

THE INVARIANT: every `scratchpad/<name>.<ext>` path named by a COMMITTED doc must
resolve in a FRESH CLONE. `scratchpad/` is tracked on purpose (knives, probes,
characterisations, run summaries — the evidence a spec's findings rest on), so a
citation that dead-ends means that spec's evidence cannot be re-run by anybody.

Filed 2026-08-26 by D-KNIFEGUARD, which found 19 cited scripts untracked and 9
cited paths absent from the tree entirely. Same family as `audit_citations.py`
check 4 (a citation that dead-ends in the private workbench): a citation must
RESOLVE, and where it dead-ends only changes the remedy.

THREE FINDING CLASSES, because they have three different remedies:

  GONE       the path is not on disk at all. Nobody can re-run that evidence,
             and if it was never committed nobody can restore it either. The
             remedy is a JUDGEMENT (restore, repoint, or reword), never a
             `git add`.
  IGNORED    on disk but excluded by .gitignore (`scratchpad/*.sh` / `*.txt` /
             `*.log`). It exists for its author and for nobody else, and no
             `git add` fixes it: the ignore rule and the citation contradict each
             other, and one of them has to give.
  UNTRACKED  on disk, in a trackable class, simply not committed. `git add`.

🔴 IT MATCHES THE PATH, NOT THE BASENAME, AND THE FILED ITEM IS WHY. A basename
detector run in D-KNIFEGUARD flagged `fastgates.py`, whose only "citation" was
the TODO sentence listing it as NOT in the class — a checker whose corpus
contains the note describing its exception will flag the exception. Requiring the
`scratchpad/` prefix costs nothing and removes it: PROSE NAMES A FILE, A CITATION
NAMES A PATH. The same rule is what lets this file's own spec discuss the class
in prose (and write `scratchpad/<name>.py`, which the pattern cannot match).

⚠️ THE SELF-TEST IS A CONTROL, NOT DECORATION. `audit_citations.py` shipped four
self-test tables that had been emptied to `[]` for the tool's whole life, printing
0/0 and exiting 0 (the 0/0-ALL-CONVERGED shape). So: the table is FLOORED, and it
must carry a vector of EACH SENSE — a citation that must be found, a bare basename
that must NOT be, and each finding class. A misclassification exits 2.

Exit status: 0 = clean, 1 = a dangling citation, 2 = the INSTRUMENT is broken
(the self-test misclassified, the corpus collapsed below its floor, or git is
unusable). 1 says the tree regressed; 2 says nothing below it was measured.

Usage:  python3 tools/check_citation_paths.py [--verbose]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# A CITATION is a path: the `scratchpad/` prefix, then a name with an extension.
# `<` and `>` are deliberately outside the character class so the placeholder
# form `scratchpad/<name>.py` — the one prose has to use to talk about this
# check at all — is not itself a citation.
CITE = re.compile(r'\bscratchpad/([A-Za-z0-9_][A-Za-z0-9_./-]*\.[A-Za-z0-9]+)')

# The corpus floor. Below this many committed docs the sweep has not run over the
# project, whatever it prints; that is an instrument fault, not a clean tree.
CORPUS_FLOOR = 100


def git(*args, check=True):
    p = subprocess.run(["git", "-C", str(ROOT), *args],
                       capture_output=True, text=True)
    if check and p.returncode != 0:
        sys.exit(f"check_citation_paths: git {' '.join(args)} failed:\n{p.stderr}")
    return p


def tracked_set() -> set[str]:
    return set(git("ls-files").stdout.split("\n")) - {""}


def ignored(paths: list[str]) -> set[str]:
    """Which of `paths` .gitignore excludes. One call, not one per path."""
    if not paths:
        return set()
    p = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "--stdin"],
                       input="\n".join(paths), capture_output=True, text=True)
    if p.returncode not in (0, 1):
        sys.exit(f"check_citation_paths: git check-ignore failed:\n{p.stderr}")
    return set(x for x in p.stdout.split("\n") if x)


def corpus() -> list[str]:
    """Every COMMITTED markdown doc. Committed, because an in-progress doc citing
    a script staged in the same commit is not a dangling citation — and because
    the invariant is about what a CLONE gets."""
    return sorted(f for f in tracked_set() if f.endswith(".md"))


def scan(files: list[str]) -> dict[str, set[str]]:
    cites: dict[str, set[str]] = {}
    for f in files:
        try:
            text = (ROOT / f).read_text(errors="replace")
        except FileNotFoundError:          # tracked but deleted in the worktree
            continue
        for m in CITE.finditer(text):
            cites.setdefault("scratchpad/" + m.group(1), set()).add(f)
    return cites


def classify(cites: dict[str, set[str]], tracked: set[str]) -> list[tuple]:
    """-> [(cls, path, citers)] for every citation that does not resolve."""
    unresolved = [p for p in cites if p not in tracked]
    on_disk = [p for p in unresolved if (ROOT / p).exists()]
    ign = ignored(on_disk)
    out = []
    for p in sorted(unresolved):
        if not (ROOT / p).exists():
            cls = "GONE"
        elif p in ign:
            cls = "IGNORED"
        else:
            cls = "UNTRACKED"
        out.append((cls, p, sorted(cites[p])))
    return out


# --- self-test ---------------------------------------------------------------
# Vectors of EACH SENSE. `want` is the citation the scanner must extract from the
# text, or None when the text must yield NO citation at all. FLOORED below.
VECTORS = [
    # (label, text, want)
    ("plain path",        "runner: `scratchpad/foo_knives.py`",   "scratchpad/foo_knives.py"),
    ("markdown link",     "[x](../scratchpad/bar.py) says",       "scratchpad/bar.py"),
    ("subdirectory",      "see scratchpad/sncap/rowdiff.py now",  "scratchpad/sncap/rowdiff.py"),
    ("non-.py class",     "the log scratchpad/run_gap.out shows", "scratchpad/run_gap.out"),
    ("hyphen in name",    "`scratchpad/a2-vpeek-impl.patch`",     "scratchpad/a2-vpeek-impl.patch"),
    # ...and the senses that must NOT fire. The first is the whole reason the
    # rule is path-anchored: D-KNIFEGUARD's basename detector flagged exactly it.
    ("bare basename",     "fastgates.py is NOT in the class",     None),
    ("prose placeholder", "for every scratchpad/<name>.py named", None),
    ("bare directory",    "`scratchpad/` has no sweep for this",  None),
    ("other directory",   "tools/p1scout.py is the live one",     None),
]
VECTOR_FLOOR = 9
SENSE_FLOOR = 2          # at least this many of each sense (fires / does not)


def selftest() -> int:
    if len(VECTORS) < VECTOR_FLOOR:
        print(f"SELF-TEST: table has {len(VECTORS)} vectors, floor is "
              f"{VECTOR_FLOOR} — the CONTROL has been blinded.")
        return 2
    pos = sum(1 for _, _, w in VECTORS if w is not None)
    if pos < SENSE_FLOOR or len(VECTORS) - pos < SENSE_FLOOR:
        print(f"SELF-TEST: {pos} must-fire / {len(VECTORS)-pos} must-not-fire "
              f"vectors; each sense needs {SENSE_FLOOR}.")
        return 2
    bad = []
    for label, text, want in VECTORS:
        got = ["scratchpad/" + m.group(1) for m in CITE.finditer(text)]
        if want is None:
            if got:
                bad.append(f"{label}: expected NO citation, got {got}")
        elif got != [want]:
            bad.append(f"{label}: expected [{want}], got {got}")
    if bad:
        print("SELF-TEST MISCLASSIFIED — the rule is broken, findings below are "
              "not trustworthy:")
        for b in bad:
            print("  " + b)
        return 2
    return 0


REMEDY = {
    "UNTRACKED": "commit it (`git add <path>`) — it is in a tracked class",
    "IGNORED":   ".gitignore excludes this class; no `git add` fixes it. Either "
                 "the citation must stop naming a path, or the ignore rule must "
                 "give",
    "GONE":      "not on disk. `git log --all -- <path>` first: a path that was "
                 "committed and moved gets REPOINTED; one that never was cannot "
                 "be restored by anyone, so the doc must stop naming a path",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true",
                    help="list every resolved citation too")
    a = ap.parse_args()

    rc = selftest()
    if rc:
        return rc

    docs = corpus()
    if len(docs) < CORPUS_FLOOR:
        print(f"CORPUS COLLAPSED: {len(docs)} committed .md files, floor is "
              f"{CORPUS_FLOOR}. Nothing below this was measured.")
        return 2

    cites = scan(docs)
    tracked = tracked_set()
    findings = classify(cites, tracked)

    print(f"citation-paths: {len(cites)} distinct scratchpad/ path(s) cited by "
          f"{len(docs)} committed doc(s)")
    if a.verbose:
        for p in sorted(cites):
            mark = "ok  " if p in tracked else "DANG"
            print(f"  {mark} {p}")
    if not findings:
        print(f"  all {len(cites)} resolve in a fresh clone.")
        return 0

    for cls in ("GONE", "IGNORED", "UNTRACKED"):
        rows = [r for r in findings if r[0] == cls]
        if not rows:
            continue
        print(f"\n{cls} ({len(rows)}): {REMEDY[cls]}")
        for _, p, citers in rows:
            print(f"  {p}")
            for c in citers:
                print(f"      cited by {c}")
    print(f"\nFAIL: {len(findings)} of {len(cites)} cited scratchpad/ path(s) do "
          f"not resolve in a fresh clone.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
