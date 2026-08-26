#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TODO sweep 2026-08-26, tranche 3 — the disk-channel items.

⚠️ A STOCK VG-8020 HAS NO DRIVE, so `diska` is False there and any row that opens
a channel can only be scored on the CF-3300 and zerobas. That is a DENOMINATOR
fact, not a result: a row with one reference says so rather than averaging.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DSK = os.path.join(ROOT, "disk", "test720.dsk")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=5.0,
                   reset=("NEW", "CLS"), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=7.0,
                   reset=("", "SCREEN 0", "NEW", "CLS"), diska=True),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=8.0, step=5.0, reset=("NEW", "CLS"), diska=True),
}
COLS, ROWS = 40, 24

CASES = [
    # T-EC6E68: FIELD #(A$<5),1 AS Z$ -- zb `Type mismatch`, VG-8020 `Illegal
    # function call`. The channel expression is a TYPE error before any drive is
    # touched, so this one may score on the diska=False side too.
    ("T-EC6E68", "field-chanexpr", ['A$="x"', 'FIELD #(A$<5),1 AS Z$', 'PRINT"[OK]"']),
    ("T-EC6E68", "control.field-ok", ['OPEN"TS.DAT"AS #1', 'FIELD #1,1 AS Z$',
                                      'PRINT"[OK]"', 'CLOSE']),
    # T-66E1EE: a non-tiling LEN=r -- cf3300 [OK], zb Syntax error.
    ("T-66E1EE", "r.len100", ['OPEN"TS.DAT"AS #1 LEN=100', 'PRINT"[";"OK";"]"',
                              'CLOSE']),
    ("T-66E1EE", "control.len128", ['OPEN"TS.DAT"AS #1 LEN=128',
                                    'PRINT"[";"OK";"]"', 'CLOSE']),
    # T-3CC9D3: a malformed filespec prints `load error` and FILES lists anyway.
    ("T-3CC9D3", "files-bad83", ['FILES"TOOLONGNAME.EXTRA"', 'PRINT"[END]"']),
    ("T-3CC9D3", "control.files-ok", ['FILES', 'PRINT"[END]"']),
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
            ("rror", "Missing", "Illegal", "mismatch", "Out of", "Bad "))]


def main():
    res = {}
    for side, cfg in SIDES.items():
        res[side] = omsx_repl.run_cases(
            cfg["machine"], [("direct", l) for _, _, l in CASES], batch=True,
            reset=cfg["reset"], boot=cfg["boot"], step=cfg["step"],
            diska=DSK if cfg["diska"] else None, verify_delivery=False)
    for i, (tid, label, lines) in enumerate(CASES):
        print(f"\n=== {tid} {label}")
        for side, cfg in SIDES.items():
            tag = "" if cfg["diska"] else "  (NO DRIVE)"
            print(f"    {side:8s} spans={spans(res[side][i])}"
                  f"  errs={errs(res[side][i])}{tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
