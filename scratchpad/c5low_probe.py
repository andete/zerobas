#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""C5-LOW: ERR 9, 10, 14 and 16's texts moved into the sub-ROM errmsg tenant.
Each printed by `ERROR n` and, where one is easy, by a real raise -- VG-8020
against both builds. The line after the typed one is the reading.
Clean room: typed BASIC and the screen.

Prediction: identical text in every row, on both builds.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK")
CASES = {"e9": "ERROR 9", "e10": "ERROR 10", "e14": "ERROR 14", "e16": "ERROR 16",
         "r9": "DIM A(5):A(9)=1", "r10": "DIM B(2):DIM B(3)",
         "r14": 'CLEAR 10:A$=STRING$(50,"x")'}


def reading(m, line):
    raw = omsx_repl.run_cases(m, [("direct", [line])], batch=False,
                              reset=("", "SCREEN 0"))[0] or ""
    flat = raw.replace("\n", "")
    rows = [flat[i:i + 40].strip() for i in range(0, len(flat), 40)]
    rows = [r for r in rows if r]
    i = max((k for k, r in enumerate(rows) if r == line), default=-1)
    return rows[i + 1] if 0 <= i < len(rows) - 1 else None


def main():
    bad = 0
    for k, line in CASES.items():
        got = [reading(m, line) for m in MACHINES]
        if got[0] is None:                 # the first cut "agreed" on None x3
            print(f"{k:4s} INSTRUMENT FAULT: the VG-8020 gave no reading")
            return 2
        same = got[1] == got[0] and got[2] == got[0]
        bad += not same
        print(f"{k:4s} {line:30s} VG [{got[0]}]  nodisk [{got[1]}]  disk [{got[2]}]"
              f"  {'SAME' if same else 'DIVERGES'}", flush=True)
    print(f"\n{'PASS' if not bad else 'FAIL'}: {len(CASES) - bad}/{len(CASES)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
