#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCOVF -- the VG-8020 reference is returning the SAME plane for every row.

scratchpad/circovf_rigcheck.py re-asked the one CIRCLE row whose answer is
already MEASURED (D-CIRCDOM §4.1: 421 px, sha1 2f6257f6, byte-identical on both
machines) under four different driving parameters. The reference answered
5133 px / bbox (0,0,255,127) / sha1 5005697b to ALL FOUR, including the exact
parameters D-CIRCDOM itself used. zerobas answered 421/2f6257f6 every time.

So the fault is not `step=`, and it is not my rows: it is the reference side.

This asks what a DEAD SUBJECT scores -- delete the CIRCLE statement entirely and
read the plane. If a program that draws NOTHING still reads ~5133 px, the
reference is not running (or not being read in) SCREEN 2 at all, and every
"reference" figure this session has produced is the same non-reading. bbox
(0,0,255,127) is VRAM $0000-$0FFF, which is where a TEXT mode keeps its pattern
generator -- the shape a font makes, not the shape a circle makes.

    python3 -u scratchpad/circovf_refdiag.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, HERE)

import omsx_repl                                    # noqa: E402
from circovf_calib import reduce_plane              # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                    "C-BIOS_MSX1_EU_REPACK_DISK")
PLANE = [(0, 6144)]


def prog(stmts):
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


def red(hexs):
    if not hexs:
        return None
    b = bytes.fromhex(hexs)
    return ("SHORT", len(b), None) if len(b) != 6144 else reduce_plane(b)


CASES = [
    ("dead_subject", ["COLOR15,4,7:SCREEN2"],
     "THE FALSIFICATION: no CIRCLE at all. A blank SCREEN 2 pattern plane is "
     "0 px. Anything else means the reading is not of SCREEN 2."),
    ("one_pixel", ["COLOR15,4,7:SCREEN2", "PSET(0,0),15"],
     "one pixel, at plane byte 0 bit 7. 1 px, bbox (0,0,0,0)."),
    ("tiny_circle", ["COLOR15,4,7:SCREEN2", "CIRCLE(40,40),4,15"],
     "the gate's own smallest CIRCLE row (circ_r4), green in "
     "graphics-acceptance for months."),
    ("known_row", ["COLOR15,4,7:SCREEN2", "CIRCLE(128,96),700,,,,.137"],
     "D-CIRCDOM §4.1: 421 px, sha1 2f6257f6 on BOTH machines."),
]


def main():
    print("=== D-CIRCOVF: what does a DEAD SUBJECT score on each machine? ===\n")
    for lbl, stmts, why in CASES:
        specs = [(lbl, prog(stmts))]
        r = red(omsx_repl.run_cases(REF, specs, batch=False,
                                    capture=("vram_segs", PLANE))[0])
        z = red(omsx_repl.run_cases(ZB, specs, batch=False,
                                    capture=("vram_segs", PLANE))[0])
        print(f"  {lbl:14} {' : '.join(stmts)}")
        print(f"        ref = {r}")
        print(f"        zb  = {z}")
        print(f"        expect: {why}")
    print()
    print("--- and what the reference's SCREEN TEXT says (no hold loop) ---")
    for lbl, stmts, _ in CASES[2:]:
        out = omsx_repl.run_cases(REF, [(lbl, stmts)], batch=False)[0]
        print(f"  {lbl}: {out!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
