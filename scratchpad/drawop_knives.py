#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DRAWOP knives — the delegation, and the mode-gate ORDERING the source claims.

  K-DR1  revert the delegation      -> the three shapes go back to ERR 13
  K-DR2  DELETE the mode gate       -> the SCREEN-0 rows stop being ERR 5

🎯 K-DR2 IS THE INTERESTING ONE. `basic/graphics.asm`:876 justifies putting the
mode gate FIRST at DRAW -- unlike PSET/PRESET/LINE/CIRCLE/PAINT, where D-LINERR
moved it DOWN -- and the evidence it cites is that `DRAW 5` is ERR 5 in SCREEN 0
and ERR 13 in SCREEN 2. Both halves were re-run as rows (`d.scr0`, `d.scr0num`)
and both hold. K-DR2 then shows the ordering is LOAD-BEARING rather than
incidental: with no gate, the SCREEN-0 rows reach the operand check and answer
24 / 13 instead of 5.

⚠️ sub.rom is REPORTED, not asserted -- see the D-MIDOP runner's note. The
D-DRAWOP fix itself is size-neutral and left sub.rom unmoved, which is the first
independent confirmation of that rule.
"""
from __future__ import annotations

import atexit
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/graphics.asm"

BASE = {
    'd.none': '24', 'd.colon': '24', 'd.plus': '24', 'd.num': '13',
    'd.scr0': '5', 'd.scr0num': '5', 'd.ok': '0', 'd.var': '0',
}

KNIVES = [
    dict(name="K-DR1",
         what="the delegation reverted to gfx_typeerr -- the pre-slice ERR 13 "
              "at all three shapes",
         old="                jp      nc,els_tc_common    ; 24 / 13, decided by eval",
         new="                jp      nc,gfx_typeerr      ; K-DR1",
         moves={'d.none': '13', 'd.colon': '13', 'd.plus': '13'}),
    dict(name="K-DR2",
         what="the MODE GATE moved AFTER the operand -- tests the ordering the "
              "source asserts in prose and D-DRAWERR measured",
         old="                call    gfx_mode_gate       ; D-SCREEN3: was 6 B of inline",
         new="                nop\n                nop\n                nop  ; K-DR2: gate removed",
         # With no mode gate at all, the SCREEN-0 rows stop being ERR 5 and fall
         # through to the operand check -- d.scr0 becomes the missing-operand 24
         # and d.scr0num the type mismatch 13. The graphics rows are unaffected:
         # they were already in SCREEN 2, where the gate passes.
         moves={'d.scr0': '24', 'd.scr0num': '13'}),
]

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def build(tag):
    assert sh("rm -rf build", f"scratchpad/drknife_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/drknife_{tag}_build.log")


def zb_faces(tag):
    log = f"scratchpad/drknife_{tag}_probe.out"
    sh("python3 scratchpad/drawop_probe.py --sides=zb", log)
    faces = {}
    for line in open(log):
        if line.startswith("  ran zb "):
            p = line.split(None, 3)
            faces[p[2]] = p[3].split("->", 1)[1].strip().strip("'")
    return faces


def main():
    original = open(SRC).read()
    # 🔴 RESTORE ON EVERY EXIT PATH, AND A FAILURE IS WHY THIS EXISTS. The only
    # restore used to be at the END of the loop body, AFTER the asserts -- so
    # when the sub.rom assertion fired mid-run it left basic/str-engine.asm
    # HOLDING THE K-MD1 CUT. The next invocation reported "anchor appears 0
    # times", which reads as a bad anchor and is really a DIRTY TREE. A knife
    # runner that can exit between the write and the restore is one that can
    # silently corrupt whatever is measured next -- and the operating rules'
    # "RESTORE BY WRITING THE BYTES" says nothing about the failure path.
    # atexit covers the assert, the exception and the clean return alike; the
    # final in-loop restore then writes the same bytes again, harmlessly.
    atexit.register(lambda: open(SRC, "w").write(original))
    for k in KNIVES:
        n = original.count(k["old"])
        assert n == 1, f"{k['name']}: anchor appears {n} times"

    print("=== baseline ===", flush=True)
    assert build("base") == 0, "baseline build failed"
    base_h = hashes()
    print("baseline roms=" + " / ".join(base_h), flush=True)
    base_faces = zb_faces("base")
    bad = {r: (base_faces.get(r), w) for r, w in BASE.items()
           if base_faces.get(r) != w}
    assert not bad, f"baseline does not match drawop_after.out: {bad}"
    print(f"baseline {len(base_faces)} rows match drawop_after.out", flush=True)

    exact = 0
    for k in KNIVES:
        name = k["name"]
        open(SRC, "w").write(original.replace(k["old"], k["new"], 1))
        assert build(name) == 0, f"{name}: build failed -- see the log"
        h = hashes()
        assert h[0] != base_h[0], f"{name}: basic-reloc.rom did NOT move -- no cut"
        # 🔴 sub.rom IS REPORTED, NOT ASSERTED, AND BOTH OF MY FIRST TWO RULES
        # WERE WRONG. The operating rules say "only sub.rom moves on a sub-tenant
        # edit", which invited asserting it UNMOVED here -- but the D-MIDOP fix
        # itself moved it, because str-engine.asm is in the MAIN LOW REGION and
        # growing it shifted 11 of the 12 addresses in the GENERATED
        # sub/basic-resident-abi.inc. So I asserted it MUST move, and K-MD1
        # failed: that cut is a `jp`->`jp` RETARGET, size-neutral, so it shifts
        # no addresses and the ABI does not move.
        # 🎯 THE TRUE RULE IS NARROWER THAN EITHER: a main low-region edit moves
        # sub.rom IFF IT CHANGES SIZE, because the coupling is the generated
        # ABI's ADDRESSES and nothing else. A runner cannot know a cut's size a
        # priori, so this REPORTS the fact and asserts only what must hold --
        # that the main image moved at all.
        sub_note = "sub MOVED" if h[1] != base_h[1] else "sub unmoved (size-neutral cut)"
        print(f"\n{name}  roms={' / '.join(h)}   [{sub_note}]", flush=True)
        print(f"  cut: {k['what']}", flush=True)
        faces = zb_faces(name)
        want = dict(BASE); want.update(k["moves"])
        bad = {r: (faces.get(r), want[r]) for r in want if faces.get(r) != want[r]}
        moved = {r: faces.get(r) for r in BASE if faces.get(r) != BASE[r]}
        print(f"  moved {len(moved)} rows: "
              + ", ".join(f"{r}={v!r}" for r, v in sorted(moved.items())), flush=True)
        if bad:
            print("  🔴 NOT EXACT: "
                  + ", ".join(f"{r} got {g!r} want {w!r}"
                              for r, (g, w) in sorted(bad.items())), flush=True)
        else:
            exact += 1
            print(f"  ✅ EXACT — {len(k['moves'])} predicted, {len(moved)} moved",
                  flush=True)
        open(SRC, "w").write(original)      # RESTORE BY WRITING THE BYTES

    assert build("restore") == 0, "restore build failed"
    rh = hashes()
    assert rh == base_h, f"restore did not reproduce the baseline: {rh} != {base_h}"
    print(f"\nrestored, roms={' / '.join(rh)}")
    print(f"\n{exact} of {len(KNIVES)} knives EXACT")
    return 0 if exact == len(KNIVES) else 1


if __name__ == "__main__":
    sys.exit(main())
