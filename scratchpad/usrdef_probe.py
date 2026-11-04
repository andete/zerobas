#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-USRDEF, measure first (2026-11-04): USR with no DEFUSR, and USRTAB at power-on.

USRTAB ($F39A, ten words) is WORK-AREA RAM: read with PEEK, never a ROM byte.
Our own programs, one per boot, under ON ERROR; typed BASIC in, the screen out.

    python3 -u scratchpad/usrdef_probe.py [MACHINE...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CASES = {"tab": 'FOR I=0 TO 9:PRINT HEX$(PEEK(&HF39A+2*I)+256*PEEK(&HF39B+2*I));" ";:NEXT',
         "u0": "PRINT USR(0)",
         "u9": "PRINT USR9(1)",
         "ustr": 'PRINT USR("A")',
         "uand": "LPRINT USR(0) AND 0",
         "dset": "DEFUSR=0:PRINT PEEK(&HF39A);PEEK(&HF39B)",
         "clr": "CLEAR:PRINT HEX$(PEEK(&HF39A)+256*PEEK(&HF39B))",
         "new": "NEW"}
MACHINES = ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]


def main():
    for m in sys.argv[1:] or MACHINES:
        for name, d in CASES.items():
            lines = ["10 ON ERROR GOTO 90", f"20 {d}", '30 PRINT "OK":END',
                     '90 PRINT "E";ERR;ERL:END', "RUN"]
            if name == "new":    # USRTAB after NEW and a fresh program
                lines = ["10 DEFUSR=&HC000", "RUN", "NEW",
                         '10 PRINT HEX$(PEEK(&HF39A)+256*PEEK(&HF39B))', "RUN"]
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, boot=14.0,
                                      reset=("SCREEN 0:WIDTH 40", "NEW"), step=4.0,
                                      run_gap=6.0)[0]
            rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr or ""), 40)]
            if "RUN" in rows:
                k = len(rows) - 1 - rows[::-1].index("RUN")
                rows = rows[k + 1:]
            out = " | ".join(r for r in rows if r.strip() and r.strip() != "Ok") or "<NO OUTPUT>"
            print(f"{m:30s} {name:5s} [{out}]", flush=True)
    print(__import__("probe_refcache").summary())


if __name__ == "__main__":
    main()
