#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GATEBLIND K-Y192 -- prove the new `clip_noop_y192` row is live.

A row that *ought* to see a failure is worth nothing until a cut actually
reddens it (K-CN1's lesson: it cut `gfx_plot_cur` in the SUB ROM, which `PSET`
never reaches, and the rows stayed green -- a claim about the knife, not about
the rows).

`PSET` is `GFX_OP=1`: the ONLY y clip on its path is `gfx_in_range`'s
`cp 192` in the MAIN ROM (basic/graphics.asm). The tenant's `gfx_plot` has no
range test at all -- it reads GXPOS/GYPOS as "guaranteed in-range" -- so cutting
the resident test is cutting the whole clip. `cp 192` -> `cp 193`, two bytes for
two bytes, and y=192 becomes on-screen while every other row's y stays below the
old bound.

⚠️ The hash guard watches `basic-reloc.rom`, NOT `sub.rom`.

    python3 -u scratchpad/y192_knife.py
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ASM = os.path.join(REPO, "basic", "graphics.asm")
MAINROM = os.path.join(REPO, "build", "basic-reloc.rom")

OLD = ("                cp      192                 ; y <= 191 ?\n"
       "                jr      nc,gir_off          ; y >= 192 -> off-screen\n")
NEW = ("                cp      193                 ; KNIFED: y = 192 accepted\n"
       "                jr      nc,gir_off          ; y >= 192 -> off-screen\n")


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.run(cmd, shell=True, cwd=REPO, stdout=f,
                              stderr=subprocess.STDOUT).returncode


def h():
    return hashlib.sha256(open(MAINROM, "rb").read()).hexdigest()[:8]


def main() -> int:
    orig = open(ASM).read()
    if orig.count(OLD) != 1:
        print(f"🔴 cut site matches {orig.count(OLD)} times")
        return 2
    base = h()
    print(f"unknifed basic-reloc.rom = {base}")
    print("PREDICTION, written before the run: with the y clip cut,")
    print("  PSET(0,192),15 writes pattern $80 at $1800 and colour $F0 at $3800")
    print("  (the SPRITE$ pin makes the bg nibble 0, so the clash rule SETs).")
    print("  clip_noop_y192 must go FAIL as 80/f0 against the reference's 00/00;")
    print("  every other phase-A row must stay PASS.\n")
    try:
        open(ASM, "w").write(orig.replace(OLD, NEW, 1))
        if sh("make basic-reloc", "/tmp/y192_build.log") or \
                sh("make repack-machine", "/tmp/y192_inst.log"):
            print("🔴 KNIFED TREE DOES NOT BUILD")
            return 1
        cut = h()
        if cut == base:
            print(f"🔴 basic-reloc.rom UNCHANGED ({cut}) -- the cut did not take")
            return 1
        print(f"basic-reloc.rom {base} -> {cut}  (the cut took)\n")
        sh("python3 -u scratchpad/clipnoop_phasea.py", "/tmp/y192_phasea.log")
        for line in open("/tmp/y192_phasea.log"):
            if line.startswith(("  PASS", "  FAIL")):
                print(line.rstrip())
    finally:
        open(ASM, "w").write(orig)
        sh("make basic-reloc", "/tmp/y192_restore.log")
        sh("make repack-machine", "/tmp/y192_restore2.log")
        print(f"\nrestored basic-reloc.rom = {h()}  "
              f"{'OK' if h() == base else '🔴 RESTORE FAILED'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
