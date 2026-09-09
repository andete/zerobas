#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PAIRSCOUT — the carve route clone_scout cannot see: an INSTRUCTION PAIR.

`clone_scout` ranks label-BLOCKS that are identical but for one or two operands.
Every carve this tool has found sits MID-BLOCK, so clone_scout is structurally
blind to it — and its own rule ("once a group's per-member size approaches the
cost of a stub there is nothing left to take") would price a 4-byte pair as
irreducible anyway.

Four conversions off this sweep on 2026-09-08/09, main page 1 2 B -> 104 B:

    D-INCSKIP    inc hl + call skip_spaces      50 sites
    D-SKIPCOMMA  call skip_spaces + cp ','      42 sites
    D-POPEXEC    pop hl + jp exec_stmt          22 sites
    D-INCEVAL    inc hl + call eval             17 sites

THE SHAPE. A pair costing C bytes becomes a 3-byte `call`/`jp` to a helper. If the
helper can be placed so it FALLS THROUGH into the second instruction's target, it
costs only the first instruction's bytes; otherwise it costs C + a terminator.

🔴 THREE HAZARDS, EACH OF WHICH BIT ONCE:
  1. A file that `sub/` or `disk/` ALSO includes cannot use a main-ROM helper —
     that is a tenant escape. Excluded here by construction.
  2. 🔴 **WRITE THE HELPER *AFTER* CONVERTING, NOT BEFORE.** This is an
     INSTRUCTION, not a caution: the sweep must not eat the helper it just
     created, and it has happened TWICE — `skip_comma` became
     `call skip_comma / ret` and `sc_call` became `call sc_call / ret`, each an
     infinite recursion inside the routine that 43 and 16 sites had just been
     pointed at. Both times pasmo assembled it happily AND the wall figure came
     out BETTER than the correct version (a recursive helper is smaller), so the
     build and the walls both said success. The second occurrence happened with
     this very paragraph already written as a warning — which is why it now says
     "write it after" instead of "beware".
  3. A fall-through helper goes ABOVE every label sharing the target's address,
     and only if nothing reaches that address by falling forward. `exec:` and
     `exec_stmt:` share one; `eval` is the first code in its file, so the answer
     lived in main.asm's include order, not in the file.

⚠️ SO: RECONCILE THE COUNTS. removed_A == removed_B == added_calls, with comments
stripped — a script's own "converted N" reports intent, not effect. My first
reconciliation of D-POPEXEC said 18/22/22 because the pattern anchored to
end-of-line and four sites carry trailing comments.

FALSIFICATION: `--selftest` plants a pair in a synthetic file and asserts it is
counted, and asserts a file named as sub-included is skipped.
"""
from __future__ import annotations

import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def sub_included() -> set[str]:
    out = set()
    for d in ("sub", "disk"):
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if not f.endswith((".asm", ".inc")):
                continue
            for ln in open(os.path.join(d, f), encoding="utf-8", errors="ignore"):
                m = re.search(r'include\s+"basic/([^"]+)"', ln)
                if m:
                    out.add(m.group(1))
    return out


def norm(line: str) -> str:
    return " ".join(line.split(";")[0].split()).lower()


def pairs(files: dict[str, list[str]]) -> collections.Counter:
    c = collections.Counter()
    for f, lines in files.items():
        n = [norm(l) for l in lines]
        for i in range(len(n) - 1):
            a, b = n[i], n[i + 1]
            if not a or not b or a.endswith(":") or b.endswith(":"):
                continue
            if any(a.startswith(x) or b.startswith(x)
                   for x in ("db ", "dw ", "ds ", "equ", "include", "if ",
                             "endif", "else", "org")):
                continue
            c[(a, b)] += 1
    return c


def isize(i: str) -> int:
    """Crude Z80 sizing -- enough to rank, never to trust as a byte count."""
    if i.startswith(("call", "jp ")) and "(" not in i:
        return 3
    if i.startswith(("jr ", "djnz")):
        return 2
    if re.match(r"ld (ix|iy),", i):
        return 4
    if re.match(r"ld \(?[a-z]{1,2}\)?,\(?[a-z]{1,2}\)?$", i):
        return 1
    if re.match(r"ld (hl|de|bc),", i) or re.match(r"ld \([^)]*[$0-9][^)]*\),", i):
        return 3
    if re.match(r"ld [a-z],[$0-9']", i):
        return 2
    if i.startswith(("cp ", "and ", "or ", "xor ", "sub ", "add a,")) and re.search(r"[$0-9']", i):
        return 2
    if i.startswith(("sbc hl", "adc hl", "srl", "sla", "rl ", "rr ", "bit ", "set ", "res ")):
        return 2
    return 1


def selftest() -> int:
    files = {"t.asm": ["  inc hl", "  call eval", "lbl:", "  inc hl", "  call eval"]}
    c = pairs(files)
    fails = []
    if c[("inc hl", "call eval")] != 2:
        fails.append(f"planted pair not counted twice: {c[('inc hl','call eval')]}")
    if c[("call eval", "lbl:")] != 0:
        fails.append("a LABEL was treated as an instruction")
    if "readdata-body.inc" not in sub_included():
        fails.append("readdata-body.inc is not detected as sub-included -- the "
                     "tenant-escape guard would let a helper call cross into sub/")
    if isize("call skip_spaces") != 3 or isize("or a") != 1 or isize("ret") != 1:
        fails.append("the sizer disagrees with known encodings (call=3, or a=1, ret=1)")
    if fails:
        print("\U0001f534 SELFTEST FAILED")
        for x in fails:
            print("   ", x)
        return 2
    print("selftest: a planted pair is counted, a label is not an instruction, and "
          "the sub-included guard sees a real tenant body ✅")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    SUB = sub_included()
    files = {}
    for f in sorted(os.listdir("basic")):
        if f.endswith((".asm", ".inc")) and f not in SUB:
            files[f] = open(os.path.join("basic", f), encoding="utf-8").read().splitlines()
    c = pairs(files)
    rows = [(n, a, b) for (a, b), n in c.items() if n >= 8]
    rows.sort(reverse=True)
    print(f"basic/ files swept: {len(files)}   (excluded as sub-included: {len(SUB)})")
    print(f"\n{'sites':>5} {'B':>3} {'net':>5}  pair")
    live = 0
    for n, a, b in rows[:20]:
        cost = isize(a) + isize(b)
        # a converted site is a 3-byte call/jp; the helper is the pair plus a
        # terminator unless it can fall through (which this cannot know)
        net = n * (cost - 3) - (cost + 1)
        flag = "" if net > 0 else "   -- cannot win: a 3 B call is not cheaper"
        if net > 0:
            live += 1
        print(f"{n:5d} {cost:3d} {net:5d}  {a}  |  {b}{flag}")
    if not rows:
        print("   (no pair at 8+ sites)")
    print(f"\n{live} pair(s) can pay for themselves at 8+ sites.")
    print("\U0001f534 AND `net` IS A CEILING, NOT A PRICE. It assumes a helper that "
          "cannot fall through; one that can is cheaper, and the three hazards in "
          "this file's docstring are not priced at all. Read them before converting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
