#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""When does the prompt appear? (the TODO item "zerobas PRINTS ITS `ZB` PROMPT
AFTER EVERY STORED PROGRAM LINE", 2026-09-24).

Each case is typed into a freshly CLS'd screen, and the rows from the first
typed line down are compared between the VG-8020 and zerobas with `Ok` and
`ZB` normalised to one token `<P>` -- the TEXT of the prompt is Joost's ruled
difference (D-ZBCRLF), its PLACEMENT is the question. Clean room: screen
contents only.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
CASES = [
    ("store3", ["NEW", "10 A=1", "20 B=2", "30 C=3", "LIST"]),
    ("blank",  ["NEW", "", "", "PRINT 7"]),
    ("delete", ["NEW", "10 A=1", "20 B=2", "10", "LIST"]),
    ("badnum", ["NEW", "70000 A=1", "PRINT 8"]),
    ("direct", ["NEW", "PRINT 9", "PRINT 10"]),
]

def rows(raw):
    rs = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].rstrip()
          for r in range(omsx_repl.ROWS)]
    rs = ["<P>" if r.strip() in ("Ok", "ZB") else r.strip() for r in rs]
    # from the first typed line (NEW) to the last non-blank row
    try:
        i = rs.index("NEW")
    except ValueError:
        return None
    rs = rs[i:]
    while rs and not rs[-1]:
        rs.pop()
    # the function-key row is furniture on both machines
    if rs and rs[-1].lower().startswith("color"):
        rs.pop()
        while rs and not rs[-1]:
            rs.pop()
    return rs

def main():
    specs = [("direct", lines) for _k, lines in CASES]
    got = {}
    for m in (REF, ZB):
        got[m] = omsx_repl.run_cases(m, specs, batch=False, reset=("CLS",),
                                     boot=8.0, capture="screen")
    bad = 0
    for i, (k, _l) in enumerate(CASES):
        r, z = rows(got[REF][i] or ""), rows(got[ZB][i] or "")
        same = r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'}  {k}")
        print(f"   ref: {' | '.join(r or ['<none>'])}")
        print(f"   zb : {' | '.join(z or ['<none>'])}")
    print(f"\n{len(CASES) - bad}/{len(CASES)} cases place the prompt as the reference does")
    return 0

if __name__ == "__main__":
    sys.exit(main())
