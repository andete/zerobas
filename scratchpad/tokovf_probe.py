#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""RAM-gap prep: does the crunch WRITE PAST TOKBUF before tk_end refuses it?

tk_end (basic/tokenise.inc) is the ONE bound on the crunch; TOKBUF is sized
576 B to absorb "one over-long pass". But tk_loop itself has no bound, and `0#`
is two characters crunched to NINE bytes (DBL_TOKEN + 8). A 253-character line
`10 A=0#+0#+...` crunches to ~829 B, which would run ~253 B past TOKBUF's end
($EE3F) into the workspace above it (P1_BLIT, FLD_TAB, PU_FMT, FLD_DESC).

The case PEEK-sums $EE40..$EF3F before and after typing the line (the sum is
of RAM, zerobas's own workspace; on the VG-8020 the same range is free user
RAM, so it is read there only as a control), then prints ERR-free evidence the
interpreter still works.

Prediction: both machines print `Line buffer overflow`; on zerobas the sum
CHANGES (the overrun), on the VG-8020 it does not.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
SUM = "S=0:FOR I=&HEE40 TO &HEF3F:S=S+PEEK(I):NEXT:PRINT \"SUM\";S"
LONG = "10 A=" + "0#+" * 82 + "0#"


def main():
    assert len(LONG) == 253, len(LONG)
    typed = [SUM, LONG, SUM, 'PRINT "ALIVE";1+1', "LIST"]
    for m in MACHINES:
        raw = omsx_repl.run_cases(m, [("direct", typed)], batch=False,
                                  reset=("",), run_gap=6.0)[0] or ""
        flat = raw.replace("\n", "")
        rows = [flat[i:i + 40].rstrip() for i in range(0, len(flat), 40)
                if flat[i:i + 40].strip()]
        print(f"=== {m}")
        for r in rows:
            if r.startswith("0#+") or "+0#+0#" in r:
                continue                           # the echoed long line
            print("   " + r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
