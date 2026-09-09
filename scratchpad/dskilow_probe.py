#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DSKILOW — the half of D-DSKIWHERE's question that lives BELOW $C000.

WHY THIS EXISTS. D-DSKIWHERE had the CF-3300 checksum every 256-byte page of
$C000..$FFFF around two `DSKI$` reads of DIFFERENT sectors, against a same-sector
control. Exactly one page moved, and D-DSKIBYTES then showed that page holds a
~32-byte record tracking the REQUEST, not a 512-byte transfer. The item closed
with two readings still standing: either the reference's `DSKI$` really does
nothing useful and a faithful one returns "", or the sector lands somewhere the
scan could not see. It named the cheap next measurement in as many words —
*"extend D-DSKIWHERE's page scan below $C000"* — and Joost approved it: **"yes,
investigate"**.

THE INSTRUMENT is D-DSKIWHERE's, verbatim except for the window: $8000..$BFFF,
the 64 pages under it. Same two reads, same same-sector control, same stage
markers, same fence.

🔴 THIS WINDOW IS MUCH NOISIER, AND THE CONTROL IS THE ONLY THING THAT MAKES IT
READABLE. The BASIC program itself, its variables and its string heap live here,
so `s.same` will list many more pages than it did up top. That is expected and it
is exactly what the control is for: a page that moves in `s.diff` AND in
`s.same` is the probe's own footprint. Only the difference is evidence.

⚠️ AND A NEGATIVE IS STILL A READING. If nothing separates in EITHER window, the
remaining possibilities are RAM the BASIC slot configuration hides from `PEEK`
(the disk ROM's own slot, page-1 RAM behind the ROM) — not "the sector is not
read". What this can establish is where it is NOT.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

DSK = os.path.join(ROOT, "disk", "test720.dsk")
CF = "National_CF-3300"
BASE = 0x8000


def program(second_sector: int):
    """Checksum $8000..$BFFF page by page around two DSKI$ reads."""
    return [
        '10 ON ERROR GOTO 900',
        '20 DIM C(63) : D$ = ""',
        '30 A$ = DSKI$(0,0)',
        '35 PRINT "ZP"; 1; "PZ"',
        f'40 FOR P = 0 TO 63 : S = 0 : FOR I = 0 TO 255 STEP 16 : '
        f'S = S + PEEK(&H{BASE:X} + P * 256 + I) : NEXT',
        '50 C(P) = S : NEXT',
        '55 PRINT "ZP"; 2; "PZ"',
        f'60 A$ = DSKI$(0,{second_sector})',
        '65 PRINT "ZP"; 3; "PZ"',
        f'70 FOR P = 0 TO 63 : S = 0 : FOR I = 0 TO 255 STEP 16 : '
        f'S = S + PEEK(&H{BASE:X} + P * 256 + I) : NEXT',
        '80 IF S <> C(P) THEN D$ = D$ + HEX$(P) + " "',
        '90 NEXT',
        '100 PRINT "ZQ"; D$; "QZ" : END',
        '900 PRINT "ZQ"; "E"; ERR; "QZ" : END',
    ]


CASES = [
    ("s.diff", program(1),
     "read sector 0, checksum, read sector 1, checksum -- pages that MOVED"),
    ("s.same", program(0),
     "CONTROL: the IDENTICAL program with BOTH reads on sector 0. Every page "
     "listed here is the probe's own footprint and means nothing"),
]


def pages(scr):
    if scr is None:
        return None
    for g in reversed(re.findall(r"ZQ\s*([0-9A-FE ]*?)\s*QZ", scr)):
        if any(ch in g for ch in '"$;'):
            continue
        return g.strip()
    return None


def main() -> int:
    got = {}
    for label, prog, _ in CASES:
        raw = "".join(omsx_repl.run_cases(
            CF, [("direct", ["NEW"] + prog + ["RUN"])], batch=False,
            reset=("", "SCREEN 0", "NEW"), boot=14.0, step=5.0,
            run_gap=150.0, cap_gap=5.0, timeout=900.0, diska=DSK)[0] or "")
        got[label] = pages(raw)
        print(f"  {label:8s} {got[label]!r}", flush=True)
        if got[label] is None:
            st = re.findall(r"ZP\s*([0-9]+)\s*PZ", raw)
            print(f"    STAGE MARKERS REACHED: {st or 'NONE'} "
                  f"(1=DSKI$ returned, 2=first checksum pass, 3=second DSKI$)")

    d, sm = got.get("s.diff"), got.get("s.same")
    print(f"\n  window ${BASE:04X}..${BASE + 0x3FFF:04X}")
    print(f"  s.diff pages: {d!r}\n  s.same pages (NOISE): {sm!r}")
    if d is None or sm is None:
        print("\n\U0001f534 NO READING on one side -- nothing is concluded.")
        return 2
    if d.startswith("E") or sm.startswith("E"):
        print(f"\n\U0001f534 A ROW TRAPPED AN ERROR ({d!r} / {sm!r}) -- the program "
              f"did not complete, so the page lists say nothing.")
        return 2
    sep = sorted(set(d.split()) - set(sm.split()), key=lambda h: int(h, 16))
    print(f"\n  SEPARATING pages (moved for sector 1 and NOT in the control): "
          f"{sep or 'NONE'}")
    if not sep:
        print("  \U0001f7e2 NEGATIVE, AND IT IS A READING: no page of this window "
              "tracks the sector number either. Combined with D-DSKIWHERE's "
              "$C000..$FFFF result, the 512 bytes are not in either half of the "
              "PEEK-visible map -- which leaves RAM the slot configuration hides, "
              "not 'no read happened'.")
    else:
        print("  \U0001f534 A PAGE HERE TRACKS THE SECTOR. D-DSKIWHERE's conclusion "
              "was scoped to its own window and this widens it -- read the bytes "
              "next, the way D-DSKIBYTES did, before calling it the landing spot: "
              "a moved page is not a landing spot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
