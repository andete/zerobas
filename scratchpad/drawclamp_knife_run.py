#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DRAWCLAMP knife runner. Predictions are in drawclamp_knives.md, written
BEFORE any of this ran.

Each knife: patch sub/graphics.asm -> rebuild -> reinstall -> run the probe(s)
the prediction names -> restore -> rebuild -> reinstall.

⚠️ ROM-HASH GUARD ([[knife-runner-needs-a-rom-hash-guard]]): a knife whose ROM
hash equals the unknifed one did NOT take, and every row it then scores is
worthless. This asserts the hash MOVES on the cut and RETURNS on the restore --
so a silently-failed patch is an error, not a green run.

    python3 -u scratchpad/drawclamp_knife_run.py [K-DC1 ...]
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ASM = os.path.join(REPO, "sub", "graphics.asm")
SUBROM = os.path.join(REPO, "build", "sub.rom")

CLAMP_CALL = ("                call    gfx_clamp_coords    "
              "; D-DRAWCLAMP: both endpoints, as LINE\n")
BF_CALL = ("                call    gfx_bf_gxpos        "
           "; D-DRAWCLAMP: BF's own work-area residue\n")
GXPOS_NEW = """                ld      hl,(GFX_Y2)         ; the CLAMPED target y
                ld      de,(GFX_Y1)         ; the CLAMPED start y
                or      a
                sbc     hl,de               ; target.y - start.y
                jp      m,gdrw_gx_start     ; target is HIGHER up -> the start wins
                ld      hl,(GFX_X2)
                ld      (GXPOS),hl
                ld      hl,(GFX_Y2)
                ld      (GYPOS),hl
                ret"""
GXPOS_OLD = """                ld      hl,(GFX_DTY)
                ld      de,(GFX_Y1)
                or      a
                sbc     hl,de
                jp      m,gdrw_gx_start
                ld      hl,(GFX_DTX)
                ld      (GXPOS),hl
                ld      hl,(GFX_DTY)
                ld      (GYPOS),hl
                ret"""

KNIVES = {
    "K-DC1": ("delete the gfx_clamp_coords call from gdrw_move_abs",
              lambda s: s.replace(CLAMP_CALL, "", 1),
              ["char", "wa2"]),
    "K-DC2": ("revert gdrw_gxpos to the RAW GFX_DTX/GFX_DTY",
              lambda s: s.replace(GXPOS_NEW, GXPOS_OLD, 1),
              ["wa2", "char"]),
    "K-DC3": ("delete the gfx_bf_gxpos call from gfx_line_op",
              lambda s: s.replace(BF_CALL, "", 1),
              ["wa2"]),
    # 🔴 K-DC3 does not build: deleting the only call leaves gfx_bf_gxpos and
    # gbf_max16 unreachable and check_dead_code.py fails basic-reloc with
    # exactly 2 dead spans. K-DC3b is the deliverable cut -- one byte, all code
    # reachable, and it turns the per-axis MAX into a MIN.
    "K-DC3b": ("gbf_max16 ret c -> ret nc (max becomes min)",
               lambda s: s.replace(
                   "                ret     c                   "
                   "; e < l -> HL is already the max",
                   "                ret     nc                  "
                   "; KNIFED: min, not max", 1),
               ["wa2"]),
}


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.run(cmd, shell=True, cwd=REPO, stdout=f,
                              stderr=subprocess.STDOUT).returncode


def romhash():
    return hashlib.sha256(open(SUBROM, "rb").read()).hexdigest()[:8]


def build(tag):
    rc = sh("make basic-reloc", f"/tmp/knife_{tag}_build.log")
    if rc:
        return None
    rc = sh("make repack-machine", f"/tmp/knife_{tag}_install.log")
    return None if rc else romhash()


def main() -> int:
    want = [k for k in sys.argv[1:] if k in KNIVES] or list(KNIVES)
    orig = open(ASM).read()
    base = romhash()
    print(f"unknifed sub.rom = {base}\n")
    fails = 0
    try:
        for name in want:
            desc, patch, probes = KNIVES[name]
            print(f"########## {name} -- {desc}")
            cut = patch(orig)
            if cut == orig:
                print(f"  🔴 PATCH DID NOT APPLY -- {name} scores nothing")
                fails += 1
                continue
            open(ASM, "w").write(cut)
            h = build(name)
            if h is None:
                print(f"  🔴 KNIFED TREE DOES NOT BUILD (see /tmp/knife_{name}_*.log)")
                print("     -- the cut is real but unscoreable; reported, not hidden")
                fails += 1
                open(ASM, "w").write(orig)
                build(f"{name}_restore")
                continue
            if h == base:
                print(f"  🔴 ROM HASH UNCHANGED ({h}) -- THE KNIFE DID NOT TAKE")
                fails += 1
            else:
                print(f"  sub.rom {base} -> {h}  (the cut took)")
            for p in probes:
                if p == "char":
                    cmd = (f"python3 -u scratchpad/drawclamp_char.py "
                           f"--phase {name} --nocalib")
                else:
                    cmd = "python3 -u scratchpad/drawclamp_wa2.py"
                log = f"/tmp/knife_{name}_{p}.log"
                sh(cmd, log)
                print(f"  --- {p} ---")
                out = open(log).read()
                keep = [l for l in out.splitlines()
                        if l.startswith(("  agree", "  DIFF ", "        zb",
                                         "=== "))]
                print("\n".join("  " + l for l in keep))
            print()
    finally:
        open(ASM, "w").write(orig)
        h = build("restore")
        print(f"restored sub.rom = {h}  "
              f"{'OK' if h == base else '🔴 RESTORE DID NOT RETURN THE BASELINE'}")
        fails += h != base
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
