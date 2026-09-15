#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The MSX hook equates are defined TWICE and the two copies must agree.

`basic/sysvars.inc` and `disk/equates.inc` each carry their own `H_*` block: the
BASIC side CONSULTS a hook cell (`chan_gate` calls through it) and the disk side
CLAIMS it (`disk/kernel.asm`'s `hk_present` table). Fourteen names appear in both.

\U0001f534 WHY THIS EXISTS. D-DSKOHOOK (2026-09-15) found `H_DSKO` wrong in BOTH
files -- `$FDF4` where the machine says `$FDEF` -- and the defect was INVISIBLE
precisely because both files agreed on the wrong value: our disk ROM claimed the
address our BASIC consulted, so every gate read `ok`. It would only have shown
with a FOREIGN disk ROM, which claims the real `$FDEF` and leaves `$FDF4` alone.
Fixing one file and not the other would have been worse than the bug: our own
build would refuse `DSKO$` outright.

So this check does not verify the ADDRESSES (only the reference can say those --
`scratchpad/hookid_probe.py` un-claims a cell and sees which verb notices). It
verifies that the two copies cannot DRIFT APART unnoticed.
"""
import io, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ("basic/sysvars.inc", "disk/equates.inc")


def hooks(rel):
    path = os.path.join(ROOT, rel)
    src = io.open(path, encoding="utf-8", errors="replace").read()
    return {m.group(1): int(m.group(2), 16)
            for m in re.finditer(r"^(H_[A-Z0-9]+)\s+equ\s+\$([0-9A-Fa-f]{4})", src, re.M)}


def main() -> int:
    a, b = (hooks(f) for f in FILES)
    shared = sorted(set(a) & set(b))
    bad = [(n, a[n], b[n]) for n in shared if a[n] != b[n]]
    print("hook equates: %s %d, %s %d, shared %d"
          % (FILES[0], len(a), FILES[1], len(b), len(shared)))
    if not shared:
        print("\U0001f534 NO SHARED NAMES AT ALL -- this check has gone blind "
              "(a renamed block, or a changed `equ` spelling). Refusing.")
        return 2
    for n, x, y in bad:
        print("  \U0001f534 %-8s %s=$%04X  %s=$%04X" % (n, FILES[0], x, FILES[1], y))
    if bad:
        print("%d hook equate(s) DIVERGE. The BASIC side consults the cell and the "
              "disk side claims it: a split makes our own build refuse a verb it "
              "can do." % len(bad))
        return 1
    print("  all %d shared hook equate(s) agree" % len(shared))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
