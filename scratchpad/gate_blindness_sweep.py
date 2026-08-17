#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GATEBLIND -- WHICH graphics-acceptance ROWS CAN ANYTHING REDDEN?

Three gate rows were found BLIND in one week, each by re-deriving it rather
than trusting it: G3's three clip rows (D-SPOKELINE), G6's horizontal
`clip_left` (D-DRAWCLAMP) and `box_bf`, which covers seven pixels in each of two
cells so not one whole byte (D-BFBYTE). Each had been green for months while
blind to the very thing it was named for. That is a pattern, so it gets
measured instead of waited for.

Method: mutate the graphics tenant, rebuild, run the WHOLE gate, and record
which rows go red. A row that NO mutation can redden is doing no work against
this battery.

⚠️ **THE BATTERY IS THE DENOMINATOR, AND IT IS HAND-LISTED.** "No mutation
reddened it" does NOT mean "blind" -- it means "blind to these five". A row
guarding sprites or PAINT is *expected* to be untouched by a battery that
mutates the pixel, clamp, line and colour paths. The output is a CANDIDATE
roster to re-derive by hand, exactly as the three known ones were, not a
verdict. [[a-hand-listed-denominator-is-a-scope-claim]]

Every mutation is ONE instruction of the SAME LENGTH so that every span stays
reachable: `check_dead_code.py` fails `make basic-reloc` on an unreachable span,
and a tree that does not build scores nothing (K-DC3 learned that the hard way).

    python3 -u scratchpad/gate_blindness_sweep.py [--dry] [M-YBOUND ...]
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
OUT = os.path.join(HERE, "gate_blindness.json")

MUTS = {
    # label: (what it breaks, old, new)
    "M-YBOUND": (
        "gfx_plot_cur: the on-screen y bound 192 -> 191, so the BOTTOM pixel "
        "row is never plotted",
        "                cp      192\n",
        "                cp      191\n"),
    "M-CLAMPY": (
        "gfx_clamp_coords: the Y max 191 -> 190",
        "                ld      a,191               ; max: the Y rows (b=3, b=1)\n",
        "                ld      a,190               ; MUTANT\n"),
    "M-CLAMPX": (
        "gfx_clamp_coords: the X max 255 -> 254",
        "                ld      a,255               ; max: the X rows (b=4, b=2)\n",
        "                ld      a,254               ; MUTANT\n"),
    "M-BRESERR": (
        "gfx_bres_init: the ERR seed dmaj>>1 computed on the WRONG half, so "
        "every sloped line picks a different sub-pixel phase",
        "                srl     h\n                rr      l                   ; HL = dmaj >> 1\n",
        "                srl     l\n                rr      l                   ; MUTANT\n"),
    "M-COLOUR": (
        "gfx_color_rmw: the clash decision inverted (c == bg now SETS)",
        "                jr      z,gcr_clear         ; c == bg -> clear the pixel, colour untouched\n",
        "                jr      nz,gcr_clear        ; MUTANT\n"),
}


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.run(cmd, shell=True, cwd=REPO, stdout=f,
                              stderr=subprocess.STDOUT).returncode


def romhash():
    return hashlib.sha256(open(SUBROM, "rb").read()).hexdigest()[:8]


def rows_from(path):
    """label -> True if PASS, False if FAIL."""
    out = {}
    for line in open(path, errors="replace"):
        m = re.match(r"\s+(PASS|FAIL)\s+(\S+)", line)
        if m:
            out[m.group(2)] = m.group(1) == "PASS"
    return out


def main() -> int:
    want = [k for k in sys.argv[1:] if k in MUTS] or list(MUTS)
    print("=== D-GATEBLIND: which gate rows can a mutation redden? ===\n")
    for k in want:
        print(f"  {k:11} {MUTS[k][0]}")
    print(f"\n  battery size: {len(want)} mutations "
          f"(the DENOMINATOR -- see the module docstring)")
    if "--dry" in sys.argv:
        return 0

    orig = open(ASM).read()
    base = romhash()
    print(f"\nunknifed sub.rom = {base}")
    reddened, ran = {}, []
    try:
        for name in want:
            desc, old, new = MUTS[name]
            print(f"\n########## {name}")
            if old not in orig:
                print("  🔴 MUTATION SITE NOT FOUND -- scores nothing")
                continue
            open(ASM, "w").write(orig.replace(old, new, 1))
            if sh("make basic-reloc", f"/tmp/mut_{name}_build.log") \
                    or sh("make repack-machine", f"/tmp/mut_{name}_inst.log"):
                print("  🔴 MUTANT DOES NOT BUILD -- scores nothing")
                open(ASM, "w").write(orig)
                sh("make basic-reloc", "/tmp/mut_restore.log")
                sh("make repack-machine", "/tmp/mut_restore2.log")
                continue
            h = romhash()
            if h == base:
                print(f"  🔴 ROM HASH UNCHANGED ({h}) -- THE MUTATION DID NOT TAKE")
                continue
            print(f"  sub.rom {base} -> {h}; running the gate...")
            log = f"/tmp/mut_{name}_gate.log"
            sh("make graphics-acceptance", log)
            rows = rows_from(log)
            red = {r for r, ok in rows.items() if not ok}
            ran.append(name)
            for r in red:
                reddened.setdefault(r, []).append(name)
            print(f"  rows seen {len(rows)}, RED {len(red)}")
    finally:
        open(ASM, "w").write(orig)
        sh("make basic-reloc", "/tmp/mut_restore.log")
        sh("make repack-machine", "/tmp/mut_restore2.log")
        h = romhash()
        print(f"\nrestored sub.rom = {h}  "
              f"{'OK' if h == base else '🔴 RESTORE FAILED'}")

    baseline = rows_from("/tmp/claude-501/-Users-joost-projects-zerobas/"
                         "13e00bb7-78fc-44c3-9b91-8d20de78f359/scratchpad/"
                         "gate2.log")
    allrows = sorted(baseline)
    never = [r for r in allrows if r not in reddened]
    print(f"\n=== {len(allrows)} baseline rows, battery of {len(ran)}: "
          f"{len(allrows) - len(never)} reddened, {len(never)} NEVER ===")
    print("\n--- rows NO mutation in this battery could redden "
          "(CANDIDATES, not a verdict) ---")
    for r in never:
        print(f"    {r}")
    import json
    with open(OUT, "w") as f:
        json.dump(dict(battery=ran, reddened=reddened, never=never), f, indent=1)
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
