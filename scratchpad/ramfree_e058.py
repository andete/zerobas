#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TXTCEIL RAM hunt — is `$E058..$E080` ACTUALLY free? Ask the machine.

`basic/sysvars.inc` carries two comments:

    ; FREE-RAM $E058..$E080  the rest of the retired GOSUB_STK
    ; FREE-RAM $E080..$E0B8  the pre-D-FORVAR FOR stack, free since it relocated

🔴 A MAP IS STILL A READING, AND THIS TREE HAS BEEN BURNED BY EXACTLY THIS
COMMENT STYLE: `sysvars.inc` advertised *"376 B spare"* for three slices after
the window had been spent, and what caught it was the ASSEMBLER, not the note
[[deffn-ramhunt-slice]]. Hours ago D-TXTCEIL took `$E038` because it was the
delta after `SL_TOK` and nothing grepped for it; `$E038` is `CURLINE`. So this
window gets measured before anything is published into it.

THE MEASUREMENT. Fill `$E058..$E07F` with a known pattern from DIRECT mode, work
the machine over the paths this cell has to survive, read every byte back, and
count what moved. A byte that changed was written by something no map names.

🎯 THE WORKOUT IS CHOSEN FOR THE SUBJECT, NOT FOR COVERAGE. `SL_CEIL` is written
by `dl_store` on EVERY LINE ENTRY and read by the lineedit tenant, so the paths
that matter are: typing lines (the store itself), `GOSUB`/`RETURN` (this window
is the RETIRED GOSUB stack — if anything still writes it, that is what would),
`FOR`/`NEXT`, string work, and `CLEAR` (which is what moves the ceiling at all).

⚠️ NO ORACLE HERE, AND IT IS STATED RATHER THAN ASSUMED: this is a claim about
zerobas's own RAM layout. The references have an entirely different map, so the
probe runs `zb` only.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
LO, HI = 0xE058, 0xE07F           # inclusive, the first documented window
PAT = 170                         # $AA -- neither 0 nor $FF, so a plain clear or
                                  # a fill of either shows up as a change

FILL = f"FORI=&H{LO:X}TO&H{HI:X}:POKEI,{PAT}:NEXT"
# `C=C-(PEEK(I)<>PAT)` rather than `IF ... THEN`: MSX's THEN consumes to end of
# line, so a `NEXT` after it would sit INSIDE the taken branch and the loop would
# run once. A boolean is -1/0, so subtracting it counts.
COUNT = (f"C=0:FORI=&H{LO:X}TO&H{HI:X}:C=C-(PEEK(I)<>{PAT}):NEXT"
         f':PRINT"[";C;"]"')

PROG = [
    "NEW",
    FILL,
    # --- the workout, typed as PROGRAM LINES so the STORE path runs too ------
    "10 GOSUB 200",
    "20 FORJ=1TO3:GOSUB 200:NEXT",
    '30 A$="x":B$=A$+"y"+A$',
    "40 DEFFNQ(X)=X+1:D=FNQ(2)",
    "50 CLEAR 200",
    "60 END",
    "200 RETURN",
    "RUN",
    COUNT,
]


def main() -> int:
    raw = "".join(omsx_repl.run_cases(
        ZB, [("direct", PROG)], batch=False, reset=(), boot=8.0, step=6.0,
        cap_gap=12.0, timeout=400.0)[0] or "")
    rows = [raw[i * 40:(i + 1) * 40].rstrip() for i in range(24)]
    for r in rows:
        if r:
            print(r)
    m = re.search(r"\[\s*(-?\d+)\s*\]", " ".join(rows))
    print()
    if not m:
        print("\U0001f534 INSTRUMENT FAULT: no [n] reading. The run did not reach the "
              "count -- that is the probe, not an answer about the window.")
        return 2
    n = int(m.group(1))
    span = HI - LO + 1
    print(f"window ${LO:04X}..${HI:04X} ({span} B): {n} byte(s) changed")
    if n:
        print("\U0001f534 NOT FREE. Something no map names writes here; the "
              "`; FREE-RAM` comment in basic/sysvars.inc is wrong or stale.")
        return 1
    print("\U0001f7e2 every byte held the pattern through a line store, GOSUB/RETURN "
          "(this IS the retired GOSUB stack), FOR/NEXT, string work, DEF FN and "
          "CLEAR. ⚠️ That is evidence for THESE paths, not a proof of "
          "freedom -- a path this workout does not run could still write here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
