#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Reported by Vampier, 2026-10-11 (a screenshot): `321 i=0.123456789` LISTs as
`321 I=@14VxSTOP` on zerobas. The tokeniser stores a float literal as $1D
(single, 4 value bytes) or $1F (double, 8), and basic/detok.inc has no arm for
either, so LIST prints the value bytes as themselves.

What does the reference LIST for each literal shape? Typed lines, LIST, the
screen. Each literal on its own line so one bad row cannot hide another.
Clean room: typed BASIC and the screen.

Prediction: zerobas garbles every row with a fractional or exponent literal
(singles too, not only doubles); the VG-8020 shows its own normalised
spelling (a leading 0 dropped, # / ! marking the type where needed).
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
LITS = ["0.123456789", "1.5", "0.5", "1E10", "1.5#", "1.5!", "123456789",
        "3.14159265358979", "1.5D3", "2E-5", "12345678", "40000"]
LINES = ["NEW"] + [f"{100 + i} A={v}" for i, v in enumerate(LITS)] + ["LIST"]


def main():
    for m in (REF, OURS):
        raw = omsx_repl.run_cases(m, [("direct", LINES)], batch=False,
                                  reset=("", "SCREEN 0"))[0] or ""
        flat = raw.replace("\n", "")
        rows = [flat[k:k + 40].rstrip() for k in range(0, len(flat), 40)]
        i = max((k for k, r in enumerate(rows) if r.strip() == "LIST"), default=-1)
        print(f"== {m}")
        for r in rows[i + 1:]:
            if r.strip():
                print("   " + r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
