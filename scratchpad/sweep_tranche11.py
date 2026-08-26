#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TODO sweep 2026-08-26, tranche 11 — the divergences filed inside `- [x]` blocks.

Tranche 10 found 38 CLOSED blocks whose headline states a divergence, 30 of which
no keyword screen could see. These are BASIC-surface rows that have never
appeared in any listing of open work. Re-run, like everything else.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=5.0,
                   reset=("NEW", "CLS")),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=7.0,
                   reset=("", "SCREEN 0", "NEW", "CLS")),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=8.0, step=5.0, reset=("NEW", "CLS")),
}
COLS, ROWS = 40, 24

# 🔴 THE FIRST DRAFT OF THIS PROBE WAS BLIND, AND IT READ AS AGREEMENT.
# Every row did `SCREEN <n>` ... then `SCREEN 0:PRINT`, and a MODE CHANGE CLEARS
# THE SCREEN -- so an error raised in SCREEN 2/3 was wiped before the SCREEN-0
# name-table scrape ran. All six rows came back identical with no error on any
# machine, which reads as "all three agree" and was really "the instrument erased
# the answer". The fix is to trap the error and carry its CODE out as a VALUE,
# which survives any number of mode changes.
CASES = [
    ("scr3", "SCREEN 3 draws on both references; zb raises ERR 5",
     ["10 ON ERROR GOTO 100", "20 SCREEN 3:PSET(10,10),15:P=POINT(10,10)",
      '30 SCREEN 0:PRINT"[ok";P;"]":END', '100 E=ERR:SCREEN 0:PRINT"[ERR";E;"]"']),
    ("scr3.ctl", "the same in SCREEN 2 -- pins the fixture on a mode all three have",
     ["10 ON ERROR GOTO 100", "20 SCREEN 2:PSET(10,10),15:P=POINT(10,10)",
      '30 SCREEN 0:PRINT"[ok";P;"]":END', '100 E=ERR:SCREEN 0:PRINT"[ERR";E;"]"']),
    ("linetm", "LINE with a string relational coordinate: refs ERR 13, zb ERR 5",
     ["10 ON ERROR GOTO 100", '20 A$="x"', "30 SCREEN 2:LINE (0,0)-((A$<5),1)",
      '40 SCREEN 0:PRINT"[ok]":END', '100 E=ERR:SCREEN 0:PRINT"[ERR";E;"]"']),
    ("linetm.ctl", "the same LINE with a numeric coordinate -- must draw on all",
     ["10 ON ERROR GOTO 100", "30 SCREEN 2:LINE (0,0)-(5,1)",
      '40 SCREEN 0:PRINT"[ok]":END', '100 E=ERR:SCREEN 0:PRINT"[ERR";E;"]"']),
    ("scrrel", "SCREEN with a relational argument: refs IFC(5), zb Syntax error(2)",
     ["10 ON ERROR GOTO 100", "20 SCREEN (1<5)",
      '30 SCREEN 0:PRINT"[ok]":END', '100 E=ERR:SCREEN 0:PRINT"[ERR";E;"]"']),
    ("scrrel.ctl", "SCREEN 1 plainly -- pins that the fixture reaches SCREEN at all",
     ["10 ON ERROR GOTO 100", "20 SCREEN 1",
      '30 SCREEN 0:PRINT"[ok]":END', '100 E=ERR:SCREEN 0:PRINT"[ERR";E;"]"']),
]


def spans(scr):
    if scr is None:
        return None
    flat = " ".join(scr[r * COLS:(r + 1) * COLS].rstrip() for r in range(ROWS))
    out, i = [], 0
    while (a := flat.find("[", i)) >= 0 and (b := flat.find("]", a)) >= 0:
        out.append(flat[a + 1:b].strip()); i = b + 1
    return out


def errs(scr):
    if scr is None:
        return None
    rows = [scr[r * COLS:(r + 1) * COLS].strip() for r in range(ROWS)]
    return [r for r in rows if any(w in r for w in
            ("rror", "Illegal", "mismatch", "Missing", "Out of", "Overflow"))]


def main():
    res = {s: omsx_repl.run_cases(c["machine"], [("direct", l + ["RUN"]) for _, _, l in CASES],
                                  batch=True, reset=c["reset"], boot=c["boot"],
                                  step=c["step"], verify_delivery=False)
           for s, c in SIDES.items()}
    for i, (label, claim, _) in enumerate(CASES):
        print(f"\n=== {label} — {claim}")
        for side in SIDES:
            print(f"    {side:8s} spans={spans(res[side][i])}  errs={errs(res[side][i])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
