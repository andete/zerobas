#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-INPUTDNOHASH's second cause: how does a NUMBER after a letter run and a
SPACE crunch? Ours stores `OPEN"X"AS 1` as `41 53 20 31` -- the 1 left as an
ASCII digit, as if it were part of the name AS -- and the evaluator then raises
Syntax error. This reads the STORED line (program text is RAM data) on the
VG-8020 and CF-3300 and on ours, for a few bodies that separate the rules.

    python3 -u scratchpad/asnum_crunch.py
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

TXTTAB = 0xF676
BODIES = [
    'OPEN"X"AS 1',          # the case: letter run, space, digit
    'OPEN"X"AS#1',          # control: '#' between
    'OPEN"X"AS1',           # no space: is 1 part of the name?
    'A=B 1',                # a VARIABLE, space, digit
    'A=B1',                 # control: a two-char name
    'PRINT AS 12',          # two digits
    'X=AS 1.5',             # a non-integer after the space
]


def stored(machine):
    specs = [("direct", [f"1 {b}"]) for b in BODIES]
    raws = omsx_repl.run_cases(machine, specs, batch=True, reset=("NEW",),
                               capture=("stored_line", TXTTAB))
    out = []
    for raw in raws:
        b = bytes.fromhex(raw) if raw else b""
        out.append(b[4:].hex(" ") if len(b) >= 5 else None)
    return out


def main():
    ref = stored("Philips_VG_8020")
    cf = stored("National_CF-3300")
    ours = stored(os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))
    bad = 0
    for body, r, c, o in zip(BODIES, ref, cf, ours):
        same = r == o
        bad += not same
        print(f"{'AGREE   ' if same else 'DIVERGES'} {body:14} VG {r}\n"
              f"{'':24}CF {c}{'' if c == r else '   <- CF-3300 differs from the VG-8020'}\n"
              f"{'':24}zb {o}")
    print(f"\n{bad} divergence(s) of {len(BODIES)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
