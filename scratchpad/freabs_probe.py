#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FREPLUS14 follow-up (2026-10-17): the ABSOLUTE FRE(0), VG-8020 vs zerobas (diskless).
scratchpad/freshape_probe.py measured every shape against a plain `A=FRE(0)` ON THE SAME
MACHINE, so it cannot see an offset common to all shapes; dimedge's edges (K=113 on the
VG-8020, 108 here: not a multiple of 8 apart) say there is one. Each row is ONE line in a
fresh program -- the dimedge shape itself, a plain LET, a PRINT -- and prints the value
the line computed. Booted per row, as basic_probe_dimedge.py runs.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

ROWS = [("dimshape", ["NEW", '10 CLEAR 200:X=INT((FRE(0)-0)/1):PRINT"[v";X;"]"', "RUN"]),
        ("let",      ["NEW", '10 CLEAR 200:X=FRE(0):PRINT"[v";X;"]"', "RUN"]),
        ("print",    ["NEW", '10 CLEAR 200:X=0:PRINT"[v";FRE(0);"]"', "RUN"]),
        ("let2",     ["NEW", '10 CLEAR 200:X=0:X=FRE(0):PRINT"[v";X;"]"', "RUN"])]
MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")


def main():
    got = {}
    for m in MACHINES:
        raws = omsx_repl.run_cases(m, [("direct", p) for _n, p in ROWS], batch=False,
                                   reset=("CLS",), boot=8.0, capture="screen")
        for (n, _p), r in zip(ROWS, raws):
            v = [x for x in re.findall(r"\[v([^\]\[]*)\]", (r or "").replace("\n", "")) if '"' not in x]
            got[(m, n)] = v[-1].strip() if v else "NO READING"
    print(f"{'row':10} {'VG':>8} {'ZB':>8}  ZB-VG")
    for n, _p in ROWS:
        a, b = got[(MACHINES[0], n)], got[(MACHINES[1], n)]
        d = int(b) - int(a) if a.lstrip("-").isdigit() and b.lstrip("-").isdigit() else "-"
        print(f"{n:10} {a:>8} {b:>8}  {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
