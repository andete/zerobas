#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TIER 4 goal (a), SAME FREE MEMORY (Joost 2026-09-24): FRE(0) and FRE("") on
the VG-8020 and on zerobas's DISKLESS machine (both diskless, like for like), in
a few states. Each case is a fresh boot. Reports the absolute values AND each
state's delta from boot -- an offset that is constant across states is a layout
difference; a delta that differs is an ECONOMY difference (goal (c)).
Clean room: screen output only."""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
P = 'PRINT"[";FRE(0);FRE("");"]"'
CASES = [
    ("boot",    [P]),
    ("clear1k", ["CLEAR 1000", P]),
    ("clear0",  ["CLEAR 0", P]),
    ("dim100",  ["DIM A(100)", P]),
    ("dimint",  ["DIM A%(100)", P]),
    ("str100",  ['A$=STRING$(100,"X")', P]),
    ("vars",    ["A=1:B%=2:C#=3:D$=\"Q\"", P]),
    ("prog10",  ["NEW"] + [f"{10*i} REM {'X'*20}" for i in range(1, 11)] + [P]),
]

def val(raw):
    t = raw or ""
    m = re.findall(r"\[\s*(-?\d+)\s+(-?\d+)\s*\]", t)
    return tuple(int(x) for x in m[-1]) if m else None

def main():
    specs = [("direct", lines) for _k, lines in CASES]
    res = {m: omsx_repl.run_cases(m, specs, batch=False, reset=("CLS",), boot=8.0,
                                  capture="screen") for m in (REF, ZB)}
    r0, z0 = val(res[REF][0]), val(res[ZB][0])
    print(f"{'state':8} {'ref FRE(0)':>10} {'zb FRE(0)':>10} {'diff':>6}   {'ref dlt':>7} {'zb dlt':>7}   "
          f"{'ref FRE$':>8} {'zb FRE$':>8}")
    for i, (k, _l) in enumerate(CASES):
        r, z = val(res[REF][i]), val(res[ZB][i])
        if not r or not z:
            print(f"{k:8} UNREADABLE ref={r} zb={z}"); continue
        print(f"{k:8} {r[0]:10} {z[0]:10} {z[0]-r[0]:6}   {r[0]-r0[0]:7} {z[0]-z0[0]:7}   "
              f"{r[1]:8} {z[1]:8}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
