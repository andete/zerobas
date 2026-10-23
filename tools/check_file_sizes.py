#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FILESIZE (Joost, 2026-10-23: "set up 1 and 2 with a 1 MB limit") -- no file over
1 MiB goes into the repository unless tools/large-files-allow.txt names it.

0b417fb3 pushed a 21 MB probe log (an uncapped breakpoint's output) to the PUBLIC repo;
d0a6fb6e trimmed it, the history keeps it. Nothing stopped it: the gates ran with the
file staged and passed. Two layers now, one script:

  --staged   the pre-commit hook (tools/git-hooks/pre-commit): every file the commit
             adds or changes, at its STAGED size
  (default)  the gate (`make size-check`, in the static tier): every tracked file, at
             its size in the index -- catches a clone without the hook
  --selftest the check bites: a planted oversized entry is refused, an allowlisted one
             passes, and the real allowlist names only files that exist

Sizes come from git's own objects (`git cat-file`), not the working tree: the commit
carries what is staged, whatever the file on disk says now.
"""
import os
import subprocess
import sys

LIMIT = 1 << 20     # 1 MiB
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOW = os.path.join(ROOT, "tools", "large-files-allow.txt")


def git(*args, inp=None):
    return subprocess.run(["git", *args], cwd=ROOT, input=inp, capture_output=True,
                          text=True, check=True).stdout


def allowlist(path=ALLOW):
    """{path: cap} from `path  [max=BYTES]  reason` lines (# comments and blank lines
    skipped). No `max=` is no cap at all; a cap is the file's own, higher limit."""
    out = {}
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#"):
            name, _, rest = line.partition(" ")
            tok = rest.split()
            out[name] = int(tok[0][4:]) if tok and tok[0].startswith("max=") else None
    return out


def index_entries(staged_only):
    """(path, blob) for every index entry, or only those the commit adds / changes."""
    want = None
    if staged_only:
        want = set(git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").split("\0")) - {""}
    out = []
    for rec in git("ls-files", "-s", "-z").split("\0"):
        if not rec:
            continue
        meta, path = rec.split("\t", 1)
        mode, blob, _stage = meta.split()
        if mode == "160000":            # a submodule: no blob of ours
            continue
        if want is None or path in want:
            out.append((path, blob))
    return out


def sizes(entries):
    """blob sizes in one `cat-file --batch-check` round trip."""
    if not entries:
        return {}
    res = git("cat-file", "--batch-check=%(objectname) %(objectsize)",
              inp="".join(b + "\n" for _, b in entries))
    by_blob = dict(l.split() for l in res.splitlines() if l)
    return {p: int(by_blob[b]) for p, b in entries}


def offenders(path_sizes, allow):
    def cap(p):
        if p not in allow:
            return LIMIT
        return allow[p] if allow[p] is not None else float("inf")
    return sorted((s, p) for p, s in path_sizes.items() if s > max(LIMIT, cap(p)))


def selftest():
    fails = []
    big, small = LIMIT + 1, LIMIT
    if offenders({"scratchpad/x.out": big}, {}) != [(big, "scratchpad/x.out")]:
        fails.append("a planted file one byte over the limit is not refused")
    if offenders({"scratchpad/x.out": small}, {}):
        fails.append("a file exactly at the limit is refused")
    if offenders({"docs/x.md": big}, {"docs/x.md": None}):
        fails.append("an allowlisted, uncapped file is refused")
    if offenders({"TODO.md": 2 * LIMIT}, {"TODO.md": 3 * LIMIT}):
        fails.append("an allowlisted file under its own cap is refused")
    if offenders({"TODO.md": 3 * LIMIT + 1}, {"TODO.md": 3 * LIMIT}) != [(3 * LIMIT + 1, "TODO.md")]:
        fails.append("an allowlisted file over its own cap is not refused")
    tracked = set(git("ls-files", "-z").split("\0"))
    gone = [p for p in allowlist() if p not in tracked]
    if gone:
        fails.append(f"the allowlist names untracked files: {gone}")
    for f in fails:
        print("SELFTEST FAIL:", f)
    print("size-check selftest:", "FAIL" if fails else "PASS (6 arms)")
    return 1 if fails else 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    staged = "--staged" in sys.argv
    allow = allowlist()
    ps = sizes(index_entries(staged))
    bad = offenders(ps, allow)
    what = "staged file(s)" if staged else "tracked file(s)"
    if bad:
        print(f"REFUSED: {len(bad)} {what} over {LIMIT // 1024} KiB "
              f"(tools/large-files-allow.txt names the exceptions):")
        for s, p in bad:
            print(f"  {s / 1048576:6.1f} MiB  {p}")
        print("Trim a log to its meaningful head; a probe's breakpoint handlers each need a cap.")
        return 1
    print(f"size-check: {len(ps)} {what}, none over {LIMIT // 1024} KiB "
          f"outside the allowlist ({len(allow)} entr{'y' if len(allow) == 1 else 'ies'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
