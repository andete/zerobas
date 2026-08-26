#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TODO sweep 2026-08-26, tranche 2 — three items that filed an exact program.

Each row is the item's OWN fixture, re-run. ⚠️ The reset CLSes (tranche 1's did
not, and every case inherited the previous case's screen), and no row contains a
statement that can BLOCK (tranche 1's `WAIT 1,0` hung both references and voided
every case after it).
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
A25 = "A" * 25
TXTTAB = "PEEK(&HF676)+256*PEEK(&HF677)"

CASES = [
    # T-13B166: "SAVE/LOAD/BLOAD with no argument say Syntax error where both the
    # reference and D-MISS-1 say Missing operand" -- filed with a LINE NUMBER in
    # the reference wording ("Missing operand in 10"), so the fixture is STORED.
    ("T-13B166", "savebare", "stored", ["10 SAVE"]),
    ("T-13B166", "loadbare", "stored", ["10 LOAD"]),
    ("T-13B166", "bloadbare", "stored", ["10 BLOAD"]),
    ("T-13B166", "control.goodsave", "stored", ['10 PRINT"[OK]"']),

    # T-B22650: the item's own s.readary / s.readscal rows, verbatim.
    ("T-B22650", "s.readary", "stored",
     ["10 CLEAR 60", "20 DIM A$(5)", '30 B$=STRING$(25,"A")', "40 A$(1)=B$",
      f"50 DATA {A25}", "60 READ A$(2)", '70 PRINT"[OK]"']),
    ("T-B22650", "s.readscal", "stored",
     ["10 CLEAR 60", "20 DIM A$(5)", '30 B$=STRING$(25,"A")', "40 A$(1)=B$",
      f"50 DATA {A25}", "60 READ D$", '70 PRINT"[OK]"']),
    ("T-B22650", "control.nodata", "stored",
     ["10 CLEAR 60", "20 DIM A$(5)", '30 B$=STRING$(25,"A")', "40 A$(1)=B$",
      '70 PRINT"[OK]"']),

    # T-E0B04B: "After CLEAR 300,TXTTAB+1000 both references have 148 free bytes
    # and refuse a 32-byte line with Out of memory; zerobas has 646, stores it".
    ("T-E0B04B", "fre-after-clear", "direct",
     [f"CLEAR 300,{TXTTAB}+1000", 'PRINT"[";FRE(0);"]"']),
    ("T-E0B04B", "store-32b", "direct",
     [f"CLEAR 300,{TXTTAB}+1000", '100 REM 012345678901234567890123',
      'PRINT"[";FRE(0);"]"']),
    ("T-E0B04B", "control.fre-plain", "direct",
     ['CLEAR 300', 'PRINT"[";FRE(0);"]"']),
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
            ("rror", "Missing", "Illegal", "mismatch", "Out of", "Overflow"))]


def main():
    res = {}
    for side, cfg in SIDES.items():
        specs = []
        for _, _, mode, lines in CASES:
            specs.append((mode, omsx_repl.as_stored(":".join(lines))
                          if mode == "stored" and False else lines))
        res[side] = omsx_repl.run_cases(
            cfg["machine"], [(m, l) for _, _, m, l in CASES], batch=True,
            reset=cfg["reset"], boot=cfg["boot"], step=cfg["step"],
            verify_delivery=False)
    for i, (tid, label, mode, lines) in enumerate(CASES):
        print(f"\n=== {tid} {label}  ({mode})")
        for side in SIDES:
            print(f"    {side:8s} spans={spans(res[side][i])}"
                  f"  errs={errs(res[side][i])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
