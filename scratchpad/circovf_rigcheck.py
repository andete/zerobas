#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCOVF -- the reference side of circovf_char.py is an INSTRUMENT FAILURE.

Round 1 read ~5115 px, bbox (0,0,255,127), on the VG-8020 in ALL EIGHT rows --
including the four GREEN CONTROLS, whose whole purpose was to be byte-identical.
A reading that is the same on a row that must diverge and on a row that must
agree is not a measurement of the subject.

The zerobas side of the same run was EXACT on all 8 rows against the offline
model, so the divergence is in how the reference was DRIVEN, not in what was
drawn. The one thing round 1 changed from D-CIRCDOM's working instrument is
`step=25.0` (added for the long draws, per the both-None NOREAD note).

So: re-ask a row whose answer is already MEASURED -- D-CIRCDOM's
`CIRCLE(128,96),700,,,,.137` = 421 px, sha1 2f6257f6, byte-identical on both
machines -- under each driving parameter in turn. Calibrate the apparatus
against a known answer before trusting it on an unknown one.

    python3 -u scratchpad/circovf_rigcheck.py
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
LINIT = "COLOR15,4,7:SCREEN2"
PLANE = [(0, 6144)]

KNOWN = "CIRCLE(128,96),700,,,,.137"      # D-CIRCDOM §4.1: 421 px, 2f6257f6
WANT = (421, "2f6257f6")


def prog(stmts):
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


def red(hexs):
    if not hexs:
        return None
    b = bytes.fromhex(hexs)
    return ("SHORT", len(b), None) if len(b) != 6144 else reduce_plane(b)


VARIANTS = [
    ("as D-CIRCDOM (no step)", dict(batch=False)),
    ("step=25.0 (round 1)", dict(batch=False, step=25.0)),
    ("step=25.0 + boot=20", dict(batch=False, step=25.0, boot=20.0)),
    ("step=8.0", dict(batch=False, step=8.0)),
]


def main():
    print("=== D-CIRCOVF rig check: a row whose answer is already MEASURED ===")
    print(f"  {KNOWN}  -> D-CIRCDOM §4.1 measured {WANT} on BOTH machines\n")
    for name, kw in VARIANTS:
        specs = [("stored", prog([LINIT, KNOWN]))]
        r = red(omsx_repl.run_cases(REF, specs, capture=("vram_segs", PLANE),
                                    **kw)[0])
        z = red(omsx_repl.run_cases(ZB, specs, capture=("vram_segs", PLANE),
                                    **kw)[0])
        ok_r = r is not None and (r[0], r[2]) == WANT
        ok_z = z is not None and (z[0], z[2]) == WANT
        print(f"  {name:24} ref={'OK  ' if ok_r else 'BAD '} {r}")
        print(f"  {'':24} zb ={'OK  ' if ok_z else 'BAD '} {z}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
