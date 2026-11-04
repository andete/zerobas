#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-USRDEF (gate: usrdef-acceptance): USR with no DEFUSR, and USRTAB at power-on.

The VG-8020 holds $475A -- the published "Illegal function call" entry -- in all
ten USRTAB vectors at power-on (CLEAR and NEW keep them), so an unset USR is
ERR 5. zerobas zeroed them and an unset USR returned its argument (fixed
2026-11-04: basic/usr.asm clear_usrtab, basic/vars.asm usr_fcerr pinned at
$475A).

USRTAB ($F39A, ten words) is WORK-AREA RAM: read with PEEK, never a ROM byte.
Our own programs, one per boot, under ON ERROR; typed BASIC in, the screen out.

    python3 -u probes/basic/basic_probe_usrdef.py [--gate]

--gate: every row must read the same on both machines (exit 1 if not; exit 2
if a VG-8020 row gave no output -- an unread reference agrees with nothing).
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    gate = "--gate" in sys.argv
    got = {}
    for m in [a for a in sys.argv[1:] if a != "--gate"] or MACHINES:
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
            out = " | ".join(r for r in rows if r.strip() and r.strip() != "Ok"
                             and r.strip() != "ZB" and "color" not in r) or "<NO OUTPUT>"
            got[(m, name)] = out
            print(f"{m:30s} {name:5s} [{out}]", flush=True)
    print(__import__("probe_refcache").summary())
    if not gate:
        return 0
    ref, zb = MACHINES
    if any(got.get((ref, n)) == "<NO OUTPUT>" for n in CASES):
        print("BROKEN FIXTURE: a VG-8020 row gave no output")
        return 2
    bad = [n for n in CASES if got.get((ref, n)) != got.get((zb, n))]
    print(f"usrdef: {len(CASES) - len(bad)}/{len(CASES)} rows agree" + (f"; DIVERGE {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
