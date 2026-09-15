#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KEYRIG: `KEY ON` / `KEY OFF` -- SEARCH the key line, never INDEX it.

These two forms were dropped for a measured reason (`basic_probe_kwsweep.py`,
the `keykw` note): the function-key line's layout is NOT the same on the two
machines. `PEEK(&HF3B0)` (LINLEN) reads **37 on the VG-8020 and 39 here**, so the
reference's assigned string lands at name-table offset 922 while a FIXED offset
reads a space on the other side -- the first cut scored `32` from BOTH machines,
an agreement about a blank cell.

\U0001f3af THE FIX IS TO STOP INDEXING. Assign a marker character to F1, then COUNT
how many times it appears in the last row's REGION -- a range wide enough to
contain row 23 at either LINLEN (23x37 = 851, 23x39 = 897) -- with the display ON
and again with it OFF. A count is invariant to where the row starts, so LINLEN
drops out of the reading entirely.

Each case prints BOTH counts rather than their difference, so the two forms do
not read alike: `display-off` reads `3 0` and `display-on` reads `0 3`, and each
cell says which transition produced it.

\U0001f534 THE CONTROL IS c0 AND IT CAN FAIL: with NO `KEY` statement at all both
counts must be 0. If the marker is found anyway, the scan window is catching the
PROGRAM LISTING as well as the key line and every reading below it is polluted.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK")
# 🔴 NARROWED FROM 840..959 (2026-09-15). Two 120-cell scans take ~170 frames
# on this tree -- a flat ~3x the reference -- and the default capture window
# closes first, which reads as an empty cell and NOT as a verdict. 851..905
# still covers row 23's opening columns at BOTH LINLENs (37: row 23 = 851..887;
# 39: row 23 = 897..935), which is where F1's label sits.
# 🔴 AND 851..905 WAS WRONG ARITHMETIC: it assumed row 23 starts at
# 23 x LINLEN. It does not. SCREEN 0's NAME TABLE IS 40 BYTES PER ROW ON BOTH
# MACHINES regardless of LINLEN (37 vs 39 is the EDITOR's logical width), so row
# 23 starts at 23 x 40 = 920 -- which is exactly why `keykw`'s note recorded the
# reference's string at offset 922. The window is the last row, 920..959: 40
# cells, machine-independent, and two scans of it are cheap enough for the
# capture window.
LO, HI = 920, 959


def count(var):
    return ["%s=0" % var,
            "FOR I=%d TO %d" % (LO, HI),
            "IF VPEEK(I)=81 THEN %s=%s+1" % (var, var),
            "NEXT"]


def prog(first, second, assign=True):
    b = (['KEY 1,"QQQ"'] if assign else ['I=0']) + [first] + count("A") + \
        [second] + count("B") + ['PRINT"<";A;B;">"', "END"]
    return b


CASES = [
    ("c0_nokey",     prog("I=0", "I=0", assign=False)),   # control: must be 0 0
    ("c1_off_first", prog("KEY OFF", "KEY ON")),          # expect 0 3
    ("c2_on_first",  prog("KEY ON", "KEY OFF")),          # expect 3 0
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        raws = omsx_repl.run_cases(mach, [("stored", l) for _, l in CASES],
                                   batch=False, cap_gap=10.0)
        for (name, _), raw in zip(CASES, raws):
            t = " ".join("".join(raw or "").split())
            r = t.rfind("RUN")
            tail = t[r + 3:] if r >= 0 else t
            i = tail.find("<")
            j = tail.find(">", i + 1) if i >= 0 else -1
            print(f"  {name:13} {(tail[i:j+1] if i >= 0 and j > i else '?' + tail[:50])!r}",
                  flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
