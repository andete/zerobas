#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""prnumwrap-acceptance (D-PRNUMWRAP) -- a PRINT number item that does not fit
the rest of the screen line moves to the next line WHOLE.

`WIDTH 37:CLS:PRINT STRING$(n,"x");v;:PRINT"|"` on the VG-8020 and on ours;
the reading is the two screen rows ending at the `|`:

  n35  601        -> ` 601` on the next line (ours used to split it `6`|`01`)
  n30  12345678   -> the same, eight digits
  n36  7          -> ` 7`, its sign space with it
  n33  601        -> fits exactly (sign space + digits = 4 = the room left); only
                     its TRAILING space wraps, alone -- the case that separates
                     "text less its trailing space" from "the whole text"
  flt  1.5        -> a float moves the same way
  neg  -42        -> a negative (its `-` is the sign position)
  str  "AB"       -> a STRING does not move: it wraps character by character

Headless, fresh boot per case. Clean room: typed text and VRAM.
Exit 0 all agree; 1 a divergence; 2 the reference gave no reading.

    python3 -u probes/basic/basic_probe_prnumwrap.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                   # noqa: E402

REF = "Philips_VG_8020"
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
CASES = [("n35", 35, "601"), ("n30", 30, "12345678"), ("n36", 36, "7"),
         ("n33", 33, "601"), ("flt", 35, "1.5"), ("neg", 35, "-42"), ("str", 36, '"AB"')]


def reading(machine, n, v):
    line = f'WIDTH 37:CLS:PRINT STRING$({n},"x");{v};:PRINT"|"'
    raw = omsx_repl.run_cases(machine, [("rd", [line])], batch=False, reset=("CLS",))[0] or ""
    rows = [raw[i:i + 40].rstrip() for i in range(0, len(raw), 40)]
    # the printed `|` row, never the typed line (which carries `PRINT`)
    hits = [i for i, r in enumerate(rows) if "|" in r and "PRINT" not in r]
    if not hits or hits[-1] == 0:
        return None
    k = hits[-1]
    # rows as they stand (right-trimmed only): `n36` is the sign space moving WITH
    # the 7 -- stripped, ` 7` and `7` read the same and the row is blind
    return rows[k - 1] + " / " + rows[k]


def main():
    bad = 0
    for tag, n, v in CASES:
        r, z = reading(REF, n, v), reading(ZB, n, v)
        if r is None:
            print(f"INSTRUMENT FAULT: the VG-8020 gave no reading for {tag}")
            return 2
        bad += r != z
        print(f"{'ok  ' if r == z else 'DIFF'} {tag:4} VG-8020 {r!r}\n{'':10}zb      {z!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: PRINT number wrapping as on the VG-8020 ({bad} divergence(s))")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
