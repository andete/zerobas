#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GATEBLIND K-GR3/K-GR4 -- do the new error-path rows SEPARATE LINE's two
work-area writers?

A drawn LINE writes GRPACX/GRPACY twice: the resident's `gfx_work_area` (called
from `gfx_point_gate`, BEFORE the SCREEN-2 gate) and the tenant's in
`gfx_line_op`. On the drawn path each masks the other -- M-GRPAC reddened five
rows and none of the three named `grpac_*`, and M-GRPAC2 reddened NOTHING while
`w_line_off` still read `W 300 250 300 250`. A mutation battery cannot see a
value that is written twice.

In SCREEN 0 the tenant never runs, so `w_err_scr0` / `w_err_step` read a cell only
the RESIDENT can fill. The pair of cuts is the proof:

    K-GR3  resident  gfx_work_area: ld (GRPACX),bc -> ld (GRPACX),de
           predict: SEVEN rows RED -- the two new w_err_* rows PLUS the five
           M-GRPAC already reddened (attr_step, clampD_dir, w_draw_left_down,
           w_draw_up_off, w_step_after), since K-GR3 IS that cut. The nine
           drawn-path rows (grpac_line, grpac_box, grpac_step, w_line_*,
           w_box_*, w_bf_*) stay GREEN, because the tenant overwrites them.

    K-GR4  tenant    gfx_line_op:   ld (GRPACX),hl -> ld (GRPACY),hl
           predict: ZERO rows red, w_err_* included -- the tenant never runs on
           the error path and the resident covers the drawn one. This re-runs
           M-GRPAC2 against the NEW row set, so the new rows are shown to be
           SPECIFIC to the resident writer rather than merely sensitive to any
           work-area cut.

Together they say: the drawn path pins the PAIR, the error path pins the
RESIDENT, and nothing in 360 rows pins the TENANT's store on its own.

    python3 -u scratchpad/grpac_knife.py
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

CUTS = {
    "K-GR3": (os.path.join(REPO, "basic", "graphics.asm"), "basic-reloc",
              "                ld      (GRPACX),bc         ; last-referenced point X\n",
              "                ld      (GRPACX),de         ; KNIFED: fed the Y value\n"),
    "K-GR4": (os.path.join(REPO, "sub", "graphics.asm"), "sub",
              "                ld      hl,(GFX_X2)\n                ld      (GXPOS),hl\n"
              "                ld      (GRPACX),hl\n",
              "                ld      hl,(GFX_X2)\n                ld      (GXPOS),hl\n"
              "                ld      (GRPACY),hl         ; KNIFED\n"),
}


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.run(cmd, shell=True, cwd=REPO, stdout=f,
                              stderr=subprocess.STDOUT).returncode


def h(rom):
    p = os.path.join(REPO, "build", f"{rom}.rom")
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]


def main() -> int:
    rc = 0
    for name, (asm, rom, old, new) in CUTS.items():
        orig = open(asm).read()
        if orig.count(old) != 1:
            print(f"🔴 {name}: cut site matches {orig.count(old)} times")
            return 2
        base = h(rom)
        print(f"\n########## {name}  (unknifed {rom}.rom = {base})")
        try:
            open(asm, "w").write(orig.replace(old, new, 1))
            if sh("make basic-reloc", f"/tmp/{name}_build.log") or \
                    sh("make repack-machine", f"/tmp/{name}_inst.log"):
                print("🔴 KNIFED TREE DOES NOT BUILD")
                return 1
            cut = h(rom)
            if cut == base:
                print(f"🔴 {rom}.rom UNCHANGED ({cut}) -- the cut did not take")
                return 1
            print(f"{rom}.rom {base} -> {cut}  (the cut took)")
            sh("make graphics-acceptance", f"/tmp/{name}_gate.log")
            rows = red = 0
            for line in open(f"/tmp/{name}_gate.log", errors="replace"):
                m = re.match(r"\s+(PASS|FAIL)\s+(\S+)", line)
                if not m:
                    continue
                rows += 1
                if m.group(1) == "FAIL":
                    red += 1
                    print("  " + line.strip())
            print(f"  rows {rows}, RED {red}")
        finally:
            open(asm, "w").write(orig)
            sh("make basic-reloc", f"/tmp/{name}_restore.log")
            sh("make repack-machine", f"/tmp/{name}_restore2.log")
            ok = h(rom) == base
            print(f"  restored {rom}.rom = {h(rom)}  "
                  f"{'OK' if ok else '🔴 RESTORE FAILED'}")
            rc |= 0 if ok else 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
