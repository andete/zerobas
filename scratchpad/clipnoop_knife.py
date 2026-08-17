#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GATEBLIND K-CN2 -- prove the REPLACEMENT clip rows are live.

Replacing one blind row with two rows that *should* be able to see a failure is
worth nothing until a cut actually reddens them. K-CN1 tried and did NOT redden
them -- and that was a defect in the KNIFE, not evidence for the rows:

🔴 **K-CN1 CUT A ROUTINE `PSET` NEVER CALLS.** It removed the X clip from
`gfx_plot_cur` in the SUB ROM, but `PSET` is `GFX_OP=1`, whose off-screen
rejection lives in the MAIN ROM: `ex_pset` calls `gfx_in_range`
(basic/graphics.asm) and `jp nc,exec_stmt` skips the plot. The sub-ROM arm
reads GXPOS as a byte that is "0..255 guaranteed in-range" by then. Same class
as D-PAINTSEED's knife cutting a different routine -- and here it was caught
only because the rows stayed GREEN under a cut that should have reddened them.

K-CN2 cuts the real one: `gfx_in_range`'s x high-byte test, `or a` -> `xor a`,
one byte for one byte, so A is always 0 and the `jr nz,gir_off` never fires.

⚠️ The hash guard watches `basic-reloc.rom`, NOT `sub.rom` -- this is a
main-ROM edit and sub.rom does not move. A guard pointed at the wrong ROM would
report "the knife did not take" for a knife that took perfectly.

    python3 -u scratchpad/clipnoop_knife.py
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

OLD = ("                or      a                   "
       "; x high byte -> x < 0 or x > 255\n")
NEW = ("                xor     a                   "
       "; KNIFED: the x range test disabled\n")


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.run(cmd, shell=True, cwd=REPO, stdout=f,
                              stderr=subprocess.STDOUT).returncode


def h():
    return hashlib.sha256(open(MAINROM, "rb").read()).hexdigest()[:8]


def main() -> int:
    orig = open(ASM).read()
    if OLD not in orig:
        print("🔴 cut site not found")
        return 2
    base = h()
    print(f"unknifed basic-reloc.rom = {base}")
    print("PREDICTION, written before the run: clip_noop_x300 -> pattern 08 at")
    print("  $0C2C (mask $80>>(300&7)) and clip_noop_xneg -> pattern 01 at")
    print("  $00F8 (mask $80>>7). Both must go FAIL; the eight on-screen")
    print("  PSET/PRESET rows must stay PASS.\n")
    try:
        open(ASM, "w").write(orig.replace(OLD, NEW, 1))
        if sh("make basic-reloc", "/tmp/cn2_build.log") or \
                sh("make repack-machine", "/tmp/cn2_inst.log"):
            print("🔴 KNIFED TREE DOES NOT BUILD")
            return 1
        cut = h()
        if cut == base:
            print(f"🔴 basic-reloc.rom UNCHANGED ({cut}) -- the cut did not take")
            return 1
        print(f"basic-reloc.rom {base} -> {cut}  (the cut took)\n")
        sh("python3 -u scratchpad/clipnoop_phasea.py", "/tmp/cn2_phasea.log")
        for line in open("/tmp/cn2_phasea.log"):
            if line.startswith(("  PASS", "  FAIL")):
                print(line.rstrip())
    finally:
        open(ASM, "w").write(orig)
        sh("make basic-reloc", "/tmp/cn2_restore.log")
        sh("make repack-machine", "/tmp/cn2_restore2.log")
        print(f"\nrestored basic-reloc.rom = {h()}  "
              f"{'OK' if h() == base else '🔴 RESTORE FAILED'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
