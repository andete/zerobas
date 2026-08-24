#!/usr/bin/env python3
"""D-SPRITE5 knives -- the deletion fix's two claims, falsified.

The fix DELETES PUT SPRITE's 5th-argument check (graphics.asm, after the pattern)
and lets exec_stmt's boundary reject the leftover -- so the sprite is PLACED then
ERR 2. The clean-HEAD before-run (sprite5_before.out) is the natural revert
(subject rows `2 209`, raise before placement).

  K-SP1  RE-ADD the deleted `call skip_spaces / cp ',' / jp z,gfx_syntax` before
         pspr_go: the three subject rows go `2 30` -> `2 209` (raise before
         placement) -- they detect the place-then-raise ordering.
  K-SP2  pspr_go's GFX_OP `ld a,9` (attribute merge) -> `ld a,2` (POINT, a read --
         no attr-table write, and pspr_go has no overflow check so no ERR 7): every
         value row that reads a placed sprite drops to 209 (unplaced) -- the `30`
         readings are genuine placements.

⚠️ SIGNATURE: `basic/*.asm` edit -> basic-reloc.rom + merged MOVE, sub.rom NOT.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/graphics.asm"

BASE = {
    'sp.ok': '0 30', 'sp.noc': '0 30', 'sp.none': '0 209',
    'sp.5comma': '2 30', 'sp.5arg': '2 30', 'sp.5colon': '2 30',
    'sp.incomp': '2 209', 'sp.barep': '2 209',
}

PSPR = ("                ; sp.barep `2 209`, agree on both refs).\n"
        "pspr_go:\n")
GFXOP9 = "                ld      a,9                 ; GFX_OP = 9 -> tenant attribute merge\n"

KNIVES = [
    dict(name="K-SP1",
         what="RE-ADD the deleted 5th-argument check (revert to raise-before-place)",
         old=PSPR,
         new=("                ; sp.barep `2 209`, agree on both refs).\n"
              "                call    skip_spaces         ; K-SP1 revert\n"
              "                cp      ','\n"
              "                jp      z,gfx_syntax\n"
              "pspr_go:\n"),
         moves={'sp.5comma': '2 209', 'sp.5arg': '2 209', 'sp.5colon': '2 209'}),
    dict(name="K-SP2",
         what="pspr_go GFX_OP ld a,9 (merge) -> ld a,2 (POINT read, no placement)",
         old=GFXOP9,
         new="                ld      a,2                 ; K-SP2 (POINT, no place)\n",
         moves={'sp.ok': '0 209', 'sp.noc': '0 209', 'sp.5comma': '2 209',
                'sp.5arg': '2 209', 'sp.5colon': '2 209'}),
]

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def build(tag):
    assert sh("rm -rf build", f"scratchpad/spk_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/spk_{tag}_build.log")


def zb_faces(tag):
    log = f"scratchpad/spk_{tag}_probe.out"
    sh("python3 scratchpad/sprite5_probe.py --sides=zb", log)
    faces = {}
    for line in open(log):
        if line.startswith("  ran zb "):
            parts = line.split(None, 3)
            faces[parts[2]] = parts[3].strip().strip("'")
    return faces


def main():
    original = open(SRC).read()
    for k in KNIVES:
        assert original.count(k["old"]) == 1, f"{k['name']}: anchor not unique"

    print("=== baseline ===", flush=True)
    assert build("base") == 0, "baseline build failed"
    base_h = hashes()
    print("baseline roms=" + " / ".join(base_h), flush=True)
    base_faces = zb_faces("base")
    for row, want in BASE.items():
        got = base_faces.get(row)
        assert got == want, f"baseline row {row}: {got!r} != documented {want!r}"
    print(f"baseline {len(base_faces)} rows match sprite5_after.out", flush=True)

    exact = 0
    for k in KNIVES:
        name = k["name"]
        open(SRC, "w").write(original.replace(k["old"], k["new"]))
        assert build(name) == 0, f"{name}: build failed -- see the log"
        h = hashes()
        assert h[0] != base_h[0], f"{name}: basic-reloc.rom did NOT move"
        assert h[2] != base_h[2], f"{name}: merged image did NOT move"
        assert h[1] == base_h[1], f"{name}: sub.rom moved -- wrong image"
        print(f"\n{name}  roms={' / '.join(h)}", flush=True)
        print(f"  cut: {k['what']}", flush=True)
        faces = zb_faces(name)
        want = dict(BASE); want.update(k["moves"])
        bad = {r: (faces.get(r), want[r]) for r in want if faces.get(r) != want[r]}
        moved = {r: faces.get(r) for r in BASE if faces.get(r) != BASE[r]}
        print(f"  moved {len(moved)} rows: "
              + ", ".join(f"{r}={v!r}" for r, v in sorted(moved.items())), flush=True)
        if bad:
            print("  🔴 NOT EXACT: "
                  + ", ".join(f"{r} got {g!r} want {w!r}" for r, (g, w) in sorted(bad.items())),
                  flush=True)
        else:
            exact += 1
            print(f"  ✅ EXACT — {len(k['moves'])} predicted, {len(moved)} moved",
                  flush=True)
        open(SRC, "w").write(original)          # RESTORE BY WRITING THE BYTES

    assert build("restore") == 0, "restore build failed"
    rh = hashes()
    print(f"\nrestored roms={' / '.join(rh)}", flush=True)
    assert rh == base_h, f"restore did not reproduce the baseline: {rh} != {base_h}"
    print(f"{exact}/{len(KNIVES)} knives EXACT")
    return 0 if exact == len(KNIVES) else 1


if __name__ == "__main__":
    sys.exit(main())
