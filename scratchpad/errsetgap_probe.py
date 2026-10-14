#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWERRSETGAP: verify the codes the T6 error sets are said to miss, on the
VG-8020, before adding them (TODO D-KWERRSETGAP: "verify each before adding it").
Each case is a stored line `10 <stmt>` + RUN, as kwsweep's T6 rows run, so the
message and ` in 10` are both read. Prediction (2026-10-14), VG-8020: STRING$ /
SPACE$ / MID$ to-end / MID$ assign / INP / OUT -> Overflow (6); SWAP with an
unset partner -> 5, with a subscript past the DIM -> 9; VARPTR of an unset
variable -> 5, of an element past the DIM -> 9. zerobas: not predicted.
Typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

def L(stmt):
    return ["NEW", "10 " + stmt, "RUN"]

CASES = {
    "string6": L('PRINT STRING$(99999,65)'),
    "space6": L('PRINT SPACE$(32768)'),
    "midste6": L('PRINT MID$("AB",70000)'),
    "mida6": L('A$="AB":MID$(A$,70000)="X"'),
    "swap5": L('A=1:SWAP A,B'),
    "swap9": L('DIM Q(2):SWAP A,Q(9)'),
    "inp6": L('PRINT INP(99999)'),
    "out6a": L('OUT 99999,0'),
    "out6b": L('OUT 0,99999'),
    "vptr5": L('PRINT VARPTR(Z)'),
    "vptr9": L('DIM Q(2):PRINT VARPTR(Q(9))'),
}


def rows(scr, start):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if start in r:
        r = r[r.index(start) + 1:]
    return " | ".join(x for x in r if x and x not in ("Ok", "ZB"))


def main():
    only = sys.argv[1:] or list(CASES)
    bad, blind = [], []
    for name in only:
        lines = CASES[name]
        got = {}
        for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            got[side] = rows(omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=3.0)[0],
                             lines[-1])
        if got["VG"] is None:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the VG-8020 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: T6 error-set gap codes ({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
