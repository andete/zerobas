#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GATEBLIND K-XR1 -- was the 32-entry attribute-x restore pinned by ANY row?

The round-2 roster left `init_p31` as phase P's only never-reddened row, and
re-deriving it says why. `gfx_spr_xsave` / `gfx_spr_xrest` bracket CHGMOD to put
32 attribute x bytes back, because C-BIOS's mode set zeroes them and the
reference's leaves them alone. A restore is therefore only OBSERVABLE where x was
NON-ZERO before the mode set -- and the only row that set one was `init_planes`,
on PLANE 0. Every other row reads an x byte that is 0 whether the restore ran or
not: the clip_noop shape exactly, a cell that cannot hold the failure.

So the loop's COUNT should be pinnable to 1 with nothing going red. `ld b,32` ->
`ld b,1`, two bytes for two bytes, and the FULL gate runs -- a phase-P-only run
would prove nothing about the other 19 phases, and the claim here is about all of
them.

⚠️ This is a sub-tenant edit: the hash guard watches `sub.rom`.

    python3 -u scratchpad/xrest_knife.py
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ASM = os.path.join(REPO, "sub", "graphics.asm")
SUBROM = os.path.join(REPO, "build", "sub.rom")

OLD = "                ld      b,32\ngsxr_lp:\n"
NEW = "                ld      b,1                 ; KNIFED: plane 0 only\ngsxr_lp:\n"


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.run(cmd, shell=True, cwd=REPO, stdout=f,
                              stderr=subprocess.STDOUT).returncode


def h():
    return hashlib.sha256(open(SUBROM, "rb").read()).hexdigest()[:8]


def main() -> int:
    orig = open(ASM).read()
    if orig.count(OLD) != 1:
        print(f"🔴 cut site matches {orig.count(OLD)} times")
        return 2
    base = h()
    print(f"unknifed sub.rom = {base}")
    print("PREDICTION, written before the run: the NEW row init_p31_x goes FAIL")
    print("  (plane 31's x = 77 is not restored, so zerobas reads 0 where the")
    print("  reference reads 77) and EVERY OTHER ROW IN THE GATE STAYS PASS --")
    print("  including init_p31 and init_planes, whose x bytes are 0 and 60/0/0.\n")
    try:
        open(ASM, "w").write(orig.replace(OLD, NEW, 1))
        if sh("make basic-reloc", "/tmp/xr1_build.log") or \
                sh("make repack-machine", "/tmp/xr1_inst.log"):
            print("🔴 KNIFED TREE DOES NOT BUILD")
            return 1
        cut = h()
        if cut == base:
            print(f"🔴 sub.rom UNCHANGED ({cut}) -- the cut did not take")
            return 1
        print(f"sub.rom {base} -> {cut}  (the cut took)\n")
        sh("make graphics-acceptance", "/tmp/xr1_gate.log")
        rows = red = 0
        for line in open("/tmp/xr1_gate.log", errors="replace"):
            m = re.match(r"\s+(PASS|FAIL)\s+(\S+)", line)
            if not m:
                continue
            rows += 1
            if m.group(1) == "FAIL":
                red += 1
                print("  " + line.strip())
        print(f"\n  rows {rows}, RED {red}")
    finally:
        open(ASM, "w").write(orig)
        sh("make basic-reloc", "/tmp/xr1_restore.log")
        sh("make repack-machine", "/tmp/xr1_restore2.log")
        print(f"\nrestored sub.rom = {h()}  "
              f"{'OK' if h() == base else '🔴 RESTORE FAILED'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
