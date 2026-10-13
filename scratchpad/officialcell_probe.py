#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""RAM audit step 2, the first group (Joost's rule, 2026-10-13: every invented
RAM cell is checked against how the reference does the job): private cells
whose job has an OFFICIAL MSX work-area cell. Does the VG-8020 keep the job in
the official cell -- and does zerobas?

Each row runs a tiny program that makes the job happen, then PEEKs the
published address (MSX2 Technical Handbook's work-area map) and prints it in
brackets. Published addresses and typed BASIC only; no ROM byte read.

  trcflg   TRON  -> TRCFLG $F7C4 (zerobas keeps TRACEFLAG privately)
  maxfil   MAXFILES=3 -> MAXFIL $F85F (zerobas: MAXF)
  datptr   READ A from `DATA 5` -> DATPTR $F6C8 (zerobas: DATAPTR)

Prediction: the VG-8020 shows each job in its official cell (TRCFLG nonzero
under TRON, MAXFIL 3, DATPTR an address inside the program); zerobas shows none
of them -- it keeps its own copies in its workspace.
LPTPOS / PRTFLG (LPRINT) need a printer on the port; a later row.
"""
import os, sys
os.environ["ZEROBAS_REFCACHE"] = "0"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
ROWS = [
    ("trcflg", ["10 TRON:A=PEEK(&HF7C4):TROFF", '20 ?"["A"]"', "RUN"]),
    ("trcflg-ctl", ['10 A=PEEK(&HF7C4):?"["A"]"', "RUN"]),
    ("maxfil", ['10 MAXFILES=3:?"["PEEK(&HF85F)"]"', "RUN"]),
    ("maxfil-ctl", ['10 ?"["PEEK(&HF85F)"]"', "RUN"]),
    ("datptr", ['10 READ A:?"["PEEK(&HF6C8)+256*PEEK(&HF6C9)"]"', "20 DATA 5", "RUN"]),
    ("datptr-ctl", ['10 ?"["PEEK(&HF6C8)+256*PEEK(&HF6C9)"]"', "20 DATA 5", "RUN"]),
]


def main():
    print(f"{'row':12s} " + "  ".join(f"{m[:28]:>28s}" for m in MACHINES))
    for name, lines in ROWS:
        vals = []
        for m in MACHINES:
            raw = omsx_repl.run_cases(m, [("direct", ["NEW"] + lines)], batch=False,
                                      reset=("", "SCREEN 0"), run_gap=6.0)[0]
            v = omsx_repl.result_span(raw) if raw else None
            vals.append("NONE" if v is None else v.strip())
        print(f"{name:12s} " + "  ".join(f"{v:>28s}" for v in vals), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
