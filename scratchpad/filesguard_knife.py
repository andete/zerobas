#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""K-FG1 — `lfl-inp` / `lfl-inpb` PIN `do_files`' op-selector guard, where every
`FILES` row provably cannot.

K-FI1 (scratchpad/filesinp_knife.py) planted the faithful pre-fix cut and
`f.filesinp` HELD, with every plain FILES row correctly holding too. TODO.md
filed the open question as *"either the tenant does not consult DISKOP_OP on the
FILES path, or 7 is harmless there"*.

🎯 IT IS THE SECOND, AND IT IS STRUCTURAL. sub/dirverb.asm reads DISKOP_OP at
FOUR sites past the dispatch -- :260 (trailing CR/LF), :297 (field layout), :349
(the printer's own space) and :375 (the SINK, CHPUT vs LPTOUT) -- and every one
is the SAME binary test, `cp DISKOP_SEL_LFILES`:

    DISKOP_SEL_FILES  = 2      the clobber = 7 (DISKOP_SEL_FAT_READ_FILE_SECTOR)
    DISKOP_SEL_LFILES = 3

2 and 7 are both "not 3", so for FILES the clobber takes the identical branch at
all four consumers. **No FILES row can pin this guard, however the refill is
arranged** -- the filed row's VERB was wrong, not just its geometry. For LFILES
the same clobber is loud: 3 takes the LFILES branch and 7 does not, so the SINK
flips from printer to screen and the layout from one-per-line to packed.

    predicted  lfl-inp   printer listing -> <nothing>            MOVES
    predicted  lfl-inpb  screen <nothing> -> the packed listing  MOVES
    predicted  lfl-wild / lfl-all / lfl-sink / lfl-ctlp   HOLD
               (no INPUT$ in them, so nothing writes DISKOP_OP between the head
               and the call and the re-read finds the selector intact)

⚠️ THE GREEN HALF IS LOAD-BEARING. If the plain LFILES rows moved too, the cut
would be breaking the verb rather than the guard and the red would mean nothing
[[a-case-that-agrees-can-agree-for-the-wrong-reason]].

The cut itself is K-FI1's, imported rather than copied so the two knives cannot
drift apart about what "pre-fix" means.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import knife_guard                                                # noqa: E402
import filesinp_knife as K                                        # noqa: E402

SRC = os.path.join(ROOT, "basic", "files.asm")
WATCH = ("lfl-inp", "lfl-inpb", "lfl-wild", "lfl-all", "lfl-sink", "lfl-ctlp",
         "lfl-ctlf")


def rows(log: str) -> dict[str, str]:
    import re
    out = {}
    for ln in log.splitlines():
        m = re.match(r"^\s*(?:ok|DIFF|FAIL)\s+(\S+)\s+(.*)$", ln)
        if m and m.group(1) in WATCH:
            v = m.group(2).split("[")[0].strip()
            out[m.group(1)] = v
    return out


def score(tag: str) -> dict[str, str]:
    p = subprocess.run(["make", "lptverb-acceptance"], cwd=ROOT,
                       capture_output=True, text=True)
    open(os.path.join(ROOT, "scratchpad", f"filesguard_{tag}.out"), "w").write(
        p.stdout + p.stderr)
    return rows(p.stdout)


def main() -> int:
    orig = open(SRC, encoding="utf-8").read()
    base_h = knife_guard.hashes()
    base = score("base")
    print(f"base ROM {base_h}")
    for w in WATCH:
        print(f"  base {w:10s} {base.get(w, '<absent>')}")
    bad = 0
    try:
        planted = orig.replace(K.HEAD_A, K.HEAD_B, 1).replace(K.ANCHOR, K.CUT, 1)
        if planted == orig:
            print("🔴 INSTRUMENT FAULT: neither anchor matched -- the cut is stale")
            return 2
        open(SRC, "w", encoding="utf-8").write(planted)
        moved, after, _rc = knife_guard.build("scratchpad/filesguard_K-FG1", base_h)
        print("\n" + knife_guard.report("K-FG1", moved, base_h, after))
        if not moved:
            print("  K-FG1 DID NOT REACH THE ROM -- score discarded")
            return 2
        got = score("K-FG1")
        print()
        for w in WATCH:
            b, g = base.get(w, "<absent>"), got.get(w, "<absent>")
            print(f"  {w:10s} {'MOVED' if b != g else 'held ':5s} {b!r}"
                  + (f"  ->  {g!r}" if b != g else ""))
    finally:
        open(SRC, "w", encoding="utf-8").write(orig)
        _m, restored, _rc = knife_guard.build("scratchpad/filesguard_restore", base_h)
        ok = restored == base_h
        print(f"\nrestore: {base_h} -> {restored}  "
              f"{'BYTE-IDENTICAL' if ok else '🔴 DRIFT'}")
        bad += 0 if ok else 1
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
