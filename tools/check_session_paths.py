#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""No tracked file carries a path into an assistant session's private space.

zerobas is PUBLIC (since 2026-10-07): every push publishes. On 2026-10-11 four
tracked files were found carrying such paths -- a script that wrote its output
into a session's temporary directory (so it ran nowhere else), a captured
warning naming one, and two doc links into a private notes directory that is
not in the repo (dead links on the public site). None was caught, because no
gate read for them.

This reads every file in the index (`git ls-files`, so a staged new file is
covered before its commit) and refuses:

  * a session temporary directory  -- `/tmp/claude-<uid>/`
  * the private notes directory    -- `.claude/` + `projects/`

Mentions of `.claude/worktrees/...` are history in prose (a deleted worktree a
stale machine once pointed into) and are not refused. Binary files (a NUL in
the bytes) are skipped.

Exit 0 clean; 1 findings; 2 the self-test went blind.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Spelled in pieces, for two gates: so this file does not match ITSELF, and
# because temp-root-check refuses a slash-tmp-slash literal -- these are
# patterns to look for, not paths anything writes.
TMP = b"/" + b"tm" + b"p/"
RULES = (
    ("session temp dir", re.compile(re.escape(TMP) + rb"claude-[0-9]+/")),
    ("private notes dir", re.compile(rb"\.claude/" + rb"projects/")),
)


def findings(name: str, data: bytes) -> list[tuple[str, int, str]]:
    if b"\0" in data:
        return []
    out = []
    for n, line in enumerate(data.split(b"\n"), 1):
        for what, rx in RULES:
            if rx.search(line):
                out.append((name, n, what))
    return out


def selftest() -> int:
    vectors = (
        ("a session temp path is refused",
         b"x = open('/private" + TMP + b"claude-501/-Users-x/abc/scratchpad/r.json')\n", 1),
        ("a link into the notes dir is refused",
         b"([`m`](../../.claude/" + b"projects/-Users-x/memory/m.md))\n", 1),
        ("a worktree mention in prose passes",
         b"points at `.claude/worktrees/brave-curie/build/x.rom`\n", 0),
        ("a plain temp path passes", b"open('" + TMP + b"foo/bar')\n", 0),
        ("a binary file is skipped", b"\0" + TMP + b"claude-501/x\n", 0),
    )
    bad = 0
    for label, data, want in vectors:
        got = len(findings("v", data))
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}  (want {want}, got {got})")
    print(f"{len(vectors) - bad}/{len(vectors)} selftest arms pass")
    return 2 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    names = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True,
                           capture_output=True).stdout.decode().split("\0")
    names = [n for n in names if n]
    if not names:
        print("session-path-check: git ls-files listed nothing -- refusing")
        return 2
    found = []
    for n in names:
        p = os.path.join(ROOT, n)
        if not os.path.isfile(p):
            continue
        with open(p, "rb") as f:
            found += findings(n, f.read())
    for n, line, what in found:
        print(f"  {n}:{line}  {what}")
    print(f"session-path-check: {len(names)} tracked files, {len(found)} finding(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
