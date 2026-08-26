#!/usr/bin/env python3
"""D-PAINT4 knives -- the deletion fix's two claims, falsified.

The fix DELETES PAINT's trailing-token check (graphics.asm, after border B) and
lets exec_stmt's boundary reject the leftover -- so PAINT FILLS then raises ERR 2
(the reference's ordering). The clean-HEAD before-run (paint4_before3.out) is the
natural revert (subject rows `2 4`, raise before fill).

  K-PA1  RE-ADD the deleted `call skip_spaces / cp ',' / jp z,ep_syntax` before
         jr ep_draw: the three subject rows go `2 9` -> `2 4` (raise before fill),
         proving they detect the fill-then-raise ordering the fix installed.
  K-PA2  ep_draw's GFX_OP `ld a,5` (PAINT) -> `ld a,2` (POINT, a READ -- no VRAM
         write, so NO fill): every value row that reads a painted pixel drops to
         the background 4, proving the 9/15 readings are genuine fills. (The ERR
         becomes 7, not 0/2: the POINT op leaves GFX_POVF set, so ep_draw's
         overflow check fires -- incidental; the load-bearing column is the pixel.)

⚠️ SIGNATURE: `basic/*.asm` edit -> basic-reloc.rom + merged MOVE, sub.rom NOT.
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

# the post-fix zb baseline (scratchpad/paint4_after.out).
BASE = {
    'pa.color': '0 9', 'pa.plain': '0 15', 'pa.nopnt': '0 4',
    'pa.4comma': '2 9', 'pa.4arg': '2 9', 'pa.4colon': '2 9',
    'pa.3comma': '24 4', 'pa.ccomma': '2 4',
}

JR_EP = ("                ; complete (ERR 2, no fill -- agrees on both refs, pa.ccomma).\n"
         "                jr      ep_draw\n")
GFXOP5 = "                ld      a,5                 ; GFX_OP = 5 -> tenant PAINT\n"

KNIVES = [
    dict(name="K-PA1",
         what="RE-ADD the deleted trailing-token check (revert to raise-before-fill)",
         old=JR_EP,
         new=("                ; complete (ERR 2, no fill -- agrees on both refs, pa.ccomma).\n"
              "                call    skip_spaces         ; K-PA1 revert\n"
              "                cp      ','\n"
              "                jp      z,ep_syntax\n"
              "                jr      ep_draw\n"),
         moves={'pa.4comma': '2 4', 'pa.4arg': '2 4', 'pa.4colon': '2 4'}),
    dict(name="K-PA2",
         what="ep_draw GFX_OP ld a,5 (PAINT) -> ld a,2 (POINT read, no fill)",
         old=GFXOP5,
         new="                ld      a,2                 ; K-PA2 (POINT, no fill)\n",
         moves={'pa.color': '7 4', 'pa.plain': '7 4', 'pa.4comma': '7 4',
                'pa.4arg': '7 4', 'pa.4colon': '7 4'}),
]

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def build(tag):
    assert sh("rm -rf build", f"scratchpad/pak_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/pak_{tag}_build.log")


def zb_faces(tag):
    log = f"scratchpad/pak_{tag}_probe.out"
    sh("python3 scratchpad/paint4_probe.py --sides=zb", log)
    faces = {}
    for line in open(log):
        if line.startswith("  ran zb "):
            parts = line.split(None, 3)
            faces[parts[2]] = parts[3].strip().strip("'")
    return faces


def main():
    original = open(SRC).read()
    # 🔴 RESTORE ON EVERY EXIT PATH, NOT JUST THE HAPPY ONE (D-MIDOP §5.2,
    # 2026-08-26). The restore below sits at the END of the loop body, AFTER the
    # asserts -- so an assertion that fires mid-run leaves the SOURCE CUT. That
    # happened: midop_knives.py exited on a sub.rom assertion and the next
    # invocation reported "anchor appears 0 times", which reads as a bad anchor
    # and is really a dirty tree. A knife runner that can exit between the write
    # and the restore can silently corrupt whatever is measured next, and the
    # ROM-hash guard cannot see it because the hash legitimately differs.
    atexit.register(lambda: open(SRC, "w").write(original))
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
    print(f"baseline {len(base_faces)} rows match paint4_after.out", flush=True)

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
