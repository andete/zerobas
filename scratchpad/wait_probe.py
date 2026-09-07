#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-WAIT — does `WAIT port,mask[,xor]` behave like the reference?

`make kwsweep` lists WAIT crunch-only, never executed, because "it can spin
forever". That is true and is the statement's DOCUMENTED behaviour: `mask = 0`
never terminates on the reference either. So every row here is constructed to
terminate, and the construction is the interesting part.

  w.vbl   WAIT &H99,128     🎯 THE REAL FUNCTIONAL ROW, and the canonical MSX use
                            of the statement: VDP status bit 7 is the VBLANK flag,
                            set once per frame. It is the only row that proves
                            WAIT actually LOOPS rather than falling straight
                            through -- the flag is CLEAR when the WAIT is reached
                            (line 10 read the port, which clears it) and becomes
                            set within one frame, ~20 ms.
  w.two   WAIT P,V          the two-argument form, where V = INP(P) measured
                            FIRST. (INP XOR 0) AND V = V, non-zero by the guard
                            on line 20, so it terminates on the first read.
  w.three WAIT P,255,V!255  the three-argument form. (INP XOR (V XOR 255)) AND 255
                            = 255, so it terminates on the first read whatever the
                            port holds -- the xor is what makes it unconditional.
  w.err   WAIT              no arguments: a syntax error on both, and the row that
                            says the parse rejects rather than hangs.

⚠️ EVERY ROW IS ALSO PROTECTED BY THE HARNESS TIMEOUT. A row that hangs reads
`<NO READING>` rather than wedging the battery, and the fence is printed by the
program itself so a hang cannot be mistaken for a value.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (os.environ.get("ZEROBAS_BASIC_MACHINE",
                          "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
}

CASES = [
    ("w.two",   ['10 P=&HA8:V=INP(P)',
                 '20 IF V=0 THEN PRINT"ZQ";-1;"QZ":END',
                 '30 WAIT P,V',
                 '40 PRINT"ZQ";1;"QZ":END']),
    ("w.three", ['10 P=&HA8:V=INP(P):X=(V XOR 255)',
                 '30 WAIT P,255,X',
                 '40 PRINT"ZQ";2;"QZ":END']),
    ("w.vbl",   ['10 A=INP(&H99)',
                 '20 WAIT &H99,128',
                 '30 PRINT"ZQ";3;"QZ":END']),
    ("w.err",   ['10 ON ERROR GOTO 90',
                 '20 WAIT',
                 '30 PRINT"ZQ";0;"QZ":END',
                 '90 PRINT"ZQ";ERR;"QZ":END']),
]


def run(side, prog):
    machine, boot, reset = SIDES[side]
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + prog + ["RUN"])], batch=False,
        reset=(), boot=boot, step=5.0, cap_gap=12.0, timeout=300.0)[0] or "")
    m = re.search(r"ZQ\s*(-?\d+)\s*QZ", raw)
    return m.group(1) if m else "<NO READING>"


def main() -> int:
    rows = []
    for tag, prog in CASES:
        got = {s: run(s, prog) for s in SIDES}
        rows.append((tag, got))
        print(f"  {tag:9s} " + "  ".join(f"{s}={got[s]:>13s}" for s in SIDES),
              flush=True)
    print(f"\n{'row':9s} {'vg8020':>8s} {'cf3300':>8s} {'zb':>13s}   verdict")
    dis, split = [], []
    for tag, g in rows:
        v, c, z = g["vg8020"], g["cf3300"], g["zb"]
        if v != c:
            verdict = "REFS SPLIT"; split.append(tag)
        elif z != v:
            verdict = "🔴 DIFF"; dis.append(tag)
        else:
            verdict = "SAME"
        print(f"{tag:9s} {v:>8s} {c:>8s} {z:>13s}   {verdict}")
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'}"
          + (f"; REFS-SPLIT: {split}" if split else "") + " ===")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
