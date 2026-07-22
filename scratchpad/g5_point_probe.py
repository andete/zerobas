#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Ground-truth PAINT via POINT() readback on VG-8020.
POINT is queried WHILE IN SCREEN 2, stashed to vars, then printed in SCREEN 0.
Each statement on its own numbered line (avoid over-long injected lines)."""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF = "Philips_VG_8020"
# probe pixels: interior, left-border, top-edge, far-outside
Q = "A=POINT(28,28):B=POINT(16,28):C=POINT(28,16):D=POINT(10,10)"
PR = 'SCREEN0:PRINT"R";A;B;C;D:END'

CASES = [
    ("sanity_pset",   ["PSET(28,28),9"]),               # expect interior=9
    ("boxonly",       ["LINE(16,16)-(40,40),15,B"]),
    ("fill15_b15",    ["LINE(16,16)-(40,40),15,B", "PAINT(28,28),15,15"]),
    ("fill4_b15",     ["LINE(16,16)-(40,40),15,B", "PAINT(28,28),4,15"]),
    ("fill4_b4box4",  ["LINE(16,16)-(40,40),4,B", "PAINT(28,28),4,4"]),
    ("fill9_b15",     ["LINE(16,16)-(40,40),15,B", "PAINT(28,28),9,15"]),
]


def main():
    specs = []
    for label, setup in CASES:
        lines = ["COLOR15,1,1:SCREEN2:CLS"] + setup + [Q, PR]
        specs.append(("stored", lines))
    outs = omsx_repl.run_cases(REF, specs, batch=False, capture="screen",
                               step=3.0, cap_gap=3.0, timeout=60.0)
    for (label, _), o in zip(CASES, outs):
        txt = " ".join((o or "").split())
        m = re.search(r"R\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", txt)
        vals = m.groups() if m else None
        print(f"  {label:14s} interior/lborder/topedge/outside = {vals}   raw={txt[:44]!r}")


if __name__ == "__main__":
    main()
