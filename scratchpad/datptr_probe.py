#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-OFFICIAL, next cell: where does the VG-8020's DATPTR ($F6C8, the READ
position) point, in each DATA state? Measure first, then decide how zerobas's
DATAPTR + DATASTATE (0 unpositioned / 1 ready / 2 exhausted) maps onto it.

Every program has the SAME line 10 prefix shape, so line addresses are the
same on both machines (identical crunch): the value is compared directly.
Published address and typed BASIC only.

Prediction (VG-8020): RUN and RESTORE -> $8000 (TXTTAB-1); RESTORE 30 -> the
byte before line 30; after reading the first of `DATA 5,6` -> the comma; after
the last item and after `Out of DATA` -> that line's terminating 0.
"""
import os, sys
os.environ["ZEROBAS_REFCACHE"] = "0"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
P = 'PEEK(&HF6C8)+256*PEEK(&HF6C9)'
ROWS = [
    ("run", [f'10 A={P}:?"["A"]"', "20 DATA 5,6", "30 DATA 7", "RUN"]),
    ("read1of2", [f'10 READ X:A={P}:?"["A"]"', "20 DATA 5,6", "30 DATA 7", "RUN"]),
    ("read2of2", [f'10 READ X,Y:A={P}:?"["A"]"', "20 DATA 5,6", "30 DATA 7", "RUN"]),
    ("readall", [f'10 READ X,Y,Z:A={P}:?"["A"]"', "20 DATA 5,6", "30 DATA 7", "RUN"]),
    ("restore", [f'10 READ X:RESTORE:A={P}:?"["A"]"', "20 DATA 5,6", "30 DATA 7", "RUN"]),
    ("restore30", [f'10 RESTORE 30:A={P}:?"["A"]"', "20 DATA 5,6", "30 DATA 7", "RUN"]),
    ("outofdata", [f'10 ON ERROR GOTO 40:READ X,Y,Z,W', "20 DATA 5,6", "30 DATA 7",
                   f'40 A={P}:?"["A"]":END', "RUN"]),
]


def main():
    print(f"{'row':10s} " + "  ".join(f"{m[:28]:>28s}" for m in MACHINES))
    for name, lines in ROWS:
        vals = []
        for m in MACHINES:
            raw = omsx_repl.run_cases(m, [("direct", ["NEW"] + lines)], batch=False,
                                      reset=("", "SCREEN 0"), run_gap=6.0)[0]
            v = omsx_repl.result_span(raw) if raw else None
            vals.append("NONE" if v is None else f"{int(v):5d} ${int(v):04X}" if v.strip().isdigit() else v.strip())
        print(f"{name:10s} " + "  ".join(f"{v:>28s}" for v in vals), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
