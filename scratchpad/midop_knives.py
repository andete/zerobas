#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-MIDOP knives — and one of them settles a documentation disagreement.

  K-MD1  revert the delegation          -> all four shapes back to ERR 2
  K-MD2  DELETE the two pops            -> predicted to move NOTHING
  K-MD3  point the missing-'=' check at the delegation -> the site that must NOT move

🎯 K-MD2 IS NOT AN ORDINARY KNIFE. `basic/files.asm`:732 says raise_error's own
`ld sp,(SAVSTK)` discards whatever is left on the stack, and the code agrees
(interp.asm:1022 for the trap arm, :1731 for the abort arm citing 4d35b6d). The
abort-chain-returns-into-caller note says the opposite and PREDATES that fix. The
shipped code pops anyway, because popping is correct under BOTH readings and
costs 2 B -- but a knife can turn the disagreement into a reading, and that is
worth more than the 2 bytes.

⚠️ sub.rom IS REPORTED, NOT ASSERTED, AND TWO WRONG RULES GOT ME THERE. The
operating rules' "only sub.rom moves on a sub-tenant edit" invites asserting it
UNMOVED -- but the fix itself moved it, because str-engine.asm is in the MAIN LOW
REGION and growing it shifted 11 of the 12 addresses in the GENERATED
sub/basic-resident-abi.inc. So I asserted it MUST move, and K-MD1 failed: that
cut is size-neutral and shifts nothing.
🎯 A main low-region edit moves sub.rom IFF IT CHANGES SIZE. A runner cannot know
that a priori, so it reports the fact and asserts only what must hold.
"""
from __future__ import annotations

import atexit
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/str-engine.asm"

BASE = {
    'm.none': '24 69', 'm.colon': '24 69', 'm.num': '13 69', 'm.plus': '24 69',
    'm.nocomma': '2 69', 'm.noclose': '13 69', 'm.noeq': '2 69',
    'm.ok': '0 81', 'm.ok3': '0 81',
}

KNIVES = [
    dict(name="K-MD1",
         what="the delegation reverted to the blanket Syntax error -- the "
              "pre-slice answer at all four shapes",
         old="                jp      nc,ems_typecheck    ; +1 B over the `jr`",
         new="                jp      nc,ems_err_pop2     ; K-MD1",
         moves={'m.none': '2 69', 'm.colon': '2 69',
                'm.num': '2 69', 'm.plus': '2 69'}),
    dict(name="K-MD2",
         what="DELETE the two pops -- turns a documentation disagreement about "
              "whether raise_error resets SP into a reading",
         old=("                pop     de                  ; discard m\n"
              "                pop     de                  ; discard n\n"
              "                jp      els_tc_common       ; -> 24 / 13 / 2, decided by eval"),
         new="                jp      els_tc_common       ; K-MD2 (pops deleted)",
         # 🎯 PREDICTED TO MOVE NOTHING. files.asm:732 and interp.asm:1022/1731
         # say raise_error resets SP from SAVSTK on BOTH arms; the
         # abort-chain-returns-into-caller note says it does not and predates the
         # fix that made it so. If nothing moves, the pops are provably
         # unnecessary (a 2 B carve) and that note needs correcting.
         moves={}),
    dict(name="K-MD3",
         what="the missing-'=' check pointed at the delegation -- the site the "
              "measurement says must STAY ERR 2",
         old="                cp      EQ_TOKEN            ; '=' crunches to $EF\n"
             "                jr      nz,ems_err_pop2",
         new="                cp      EQ_TOKEN            ; '=' crunches to $EF\n"
             "                jp      nz,ems_typecheck    ; K-MD3",
         moves={'m.noeq': '13 69'}),
]

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def build(tag):
    assert sh("rm -rf build", f"scratchpad/mdknife_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/mdknife_{tag}_build.log")


def zb_faces(tag):
    log = f"scratchpad/mdknife_{tag}_probe.out"
    sh("python3 scratchpad/midop_probe.py --sides=zb", log)
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
    assert not bad, f"baseline does not match midop_after.out: {bad}"
    print(f"baseline {len(base_faces)} rows match midop_after.out", flush=True)

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
