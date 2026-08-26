#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TODO sweep 2026-08-26, tranche 12 — more blocks from the §1.2 set.

Reuses tranche 11's lesson: never read an error off the screen after a MODE
CHANGE, carry it out as a VALUE.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=6.0,
                   reset=("NEW", "CLS")),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=8.0,
                   reset=("", "SCREEN 0", "NEW", "CLS")),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=8.0, step=6.0, reset=("NEW", "CLS")),
}
COLS, ROWS = 40, 24

CASES = [
    # `RUN <lineno>` INSIDE A PROGRAM -- the item's own fixture verbatim.
    # (Distinct from the DIRECT-mode `RUN 20` item already verdicted LIVE.)
    ("runline.stored", "refs print B; the item says zb raises Syntax error",
     ["10 ON ERROR GOTO 100", "20 GOTO 50", '30 PRINT"[B]"', "40 END",
      "50 RUN 30", '100 E=ERR:PRINT"[ERR";E;"]"']),
    ("runline.ctl", "n.runlinectl -- all three must print B",
     ["10 ON ERROR GOTO 100", '20 PRINT"[B]"', "30 END",
      '100 E=ERR:PRINT"[ERR";E;"]"']),

    # CIRCLE r >= 256: the 16-bit product bound. Three POINT samples make a
    # signature; any machine differing on the signature is the finding.
    ("circ256", "CIRCLE(128,96),256 -- refs vs zb pixel signature",
     ["10 ON ERROR GOTO 100", "20 SCREEN 2:CIRCLE(128,96),256",
      "30 P1=POINT(0,96):P2=POINT(128,0):P3=POINT(250,96)",
      '40 SCREEN 0:PRINT"[";P1;P2;P3;"]":END',
      '100 E=ERR:SCREEN 0:PRINT"[ERR";E;"]"']),
    ("circ128.ctl", "the same at r=128, below the product bound -- must agree",
     ["10 ON ERROR GOTO 100", "20 SCREEN 2:CIRCLE(128,96),128",
      "30 P1=POINT(0,96):P2=POINT(128,0):P3=POINT(250,96)",
      '40 SCREEN 0:PRINT"[";P1;P2;P3;"]":END',
      '100 E=ERR:SCREEN 0:PRINT"[ERR";E;"]"']),
]


def spans(scr):
    if scr is None:
        return None
    flat = " ".join(scr[r * COLS:(r + 1) * COLS].rstrip() for r in range(ROWS))
    out, i = [], 0
    while (a := flat.find("[", i)) >= 0 and (b := flat.find("]", a)) >= 0:
        out.append(flat[a + 1:b].strip()); i = b + 1
    return out


def main():
    res = {s: omsx_repl.run_cases(c["machine"],
                                  [("direct", l + ["RUN"]) for _, _, l in CASES],
                                  batch=True, reset=c["reset"], boot=c["boot"],
                                  step=c["step"], verify_delivery=False)
           for s, c in SIDES.items()}
    for i, (label, claim, _) in enumerate(CASES):
        print(f"\n=== {label} — {claim}")
        for side in SIDES:
            print(f"    {side:8s} spans={spans(res[side][i])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
