#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RG7 measurement: what VDP register 7's RAM copy RG7SAV ($F3E6, published)
holds after COLOR in each screen mode. Found by the golf screen comparison
(2026-10-14): in SCREEN 1 / 2 the VG-8020's register 7 was 0 (the border) and
zerobas's $F0. Prediction: SCREEN 1 / 2 -> VG 7, ZB 247; SCREEN 0 -> 244 both.
Typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

CASES = {
    "s0": ["NEW", "10 SCREEN 0:COLOR 15,4,7:A=PEEK(&HF3E6):COLOR 15,4,4:PRINT A", "RUN"],
    "s1": ["NEW", "10 SCREEN 1:COLOR 15,4,7:A=PEEK(&HF3E6):SCREEN 0:COLOR 15,4,4:PRINT A", "RUN"],
    "s2": ["NEW", "10 SCREEN 2:COLOR 15,4,7:A=PEEK(&HF3E6):SCREEN 0:COLOR 15,4,4:PRINT A", "RUN"],
    "s3": ["NEW", "10 SCREEN 3:COLOR 15,4,7:A=PEEK(&HF3E6):SCREEN 0:COLOR 15,4,4:PRINT A", "RUN"],
    "s2c": ["NEW", "10 COLOR 15,4,7:SCREEN 2:A=PEEK(&HF3E6):SCREEN 0:COLOR 15,4,4:PRINT A", "RUN"],
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
    print(f"\n{'PASS' if not bad else 'FAIL'}: RG7SAV after COLOR ({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
