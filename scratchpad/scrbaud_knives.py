#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-SCRBAUD knives — is the new slot-3 arm OBSERVED, and did sharing the bound
leave the SPRITE-SIZE arm observed too?

The fix folded two domains onto one comparison: `C` carries the bound (4 for the
sprite size, 2 for the baud rate after `dec e` shifts 1..2 down to 0..1) so a
single `jp nc,gb_illegal` serves both, and `dec c / dec c / ret z` then reads C
back to say WHICH slot it was. That is 11 B instead of 12 and it fits; it also
means one cut can now break two features, and a cut that breaks only one is the
evidence they are still separately covered.

K-SB1  `cp c` -> `cp a`           the shared comparison, disabled
       PREDICTED "the bound accepts everything: t.b0/t.b3/a.sprbad all go
       ERR 0". 🔴 WRONG, AND BACKWARDS: `jp nc` fires when carry is CLEAR, and
       `cp a` clears it, so the cut makes the bound REJECT everything.
       ACTUAL: a.spr 0 -> 5, a.sprslot1 0 -> 5, t.b1 0 -> 5 and t.b2 0 -> 5 --
       every VALID value stops being accepted. t.b0/t.b3/a.sprbad held, because
       all three were ERR 5 already and a cut cannot move a row to where it
       already is.
       🎯 Kept, and it answers MORE than the inverted version would have: the
       shared comparison is load-bearing for BOTH slots. That only became
       visible when t.b1/t.b2 were added to the watch list for K-SB4 -- with the
       first watch list this knife looked like a size-only witness, which is a
       reading produced by the instrument's own scope
       [[a-coverage-row-whose-geometry-cannot-reach-the-case]].
K-SB2  `ld c,2` -> `ld c,4`       only the BAUD bound widens
       predict: t.b3 moves (E=3, dec E -> 2, and 2 < 4) and t.b0 does NOT
       (E=0, dec E -> 255, still >= 4); the size rows are untouched.
       ✅ EXACTLY THAT. The asymmetry is the point: a knife reddening BOTH baud
       rows would be consistent with "C is ignored", and this one cannot be.
K-SB3  `ret z` -> `ret nz`        the slot-3 / slot-1 discrimination inverts
       predict: a.spr and a.sprslot1 break while t.b0/t.b3 stay ERR 5.
       ⚠️ HALF WRONG, in a way this repo had already written down: a.sprslot1
       moved (0 -> ERROR 99, the size never applied) and **a.spr HELD** --
       a.spr reads only the error code, and a size that is never applied raises
       nothing. That is the filed blindness of a.spr, re-witnessed here.
K-SB4  `dec e` -> `nop`           the baud domain stops being SHIFTED
       🔴 ADDED BECAUSE K-SB1..3 LEFT t.b0 WITH NO KNIFE THAT MOVES IT. t.b3 is
       witnessed by K-SB2; t.b0 is rejected by the `dec e` WRAP (0 -> 255), not
       by the bound value, and no reachable bound can witness it (accepting
       E=0 through `cp c` would need a bound above 255).
       predict: t.b0 5 -> 0 (E=0 < 2 now) and t.b2 0 -> 5 (E=2 is no longer
       shifted below the bound); t.b1 and t.b3 hold.
       ✅ EXACTLY THAT, all four rows. t.b0 now has a witness.

## Scoreboard, 2026-09-06

    knife   t.b0  t.b1  t.b2  t.b3  a.spr  a.sprslot1  a.sprbad
    K-SB1    -    MOVE  MOVE   -    MOVE     MOVE         -
    K-SB2    -     -     -    MOVE   -        -           -
    K-SB3    -     -     -     -     -       MOVE         -
    K-SB4   MOVE   -    MOVE   -     -        -           -

⚠️ `a.sprbad` MOVES UNDER NOTHING HERE, and that is correct rather than a hole:
it is `SCREEN 1,99`, already ERR 5, and every cut above either widens a bound
(99 still misses it) or breaks a path it does not take. Its own witness is
K-SE4, recorded in docs/spec-basic-screenerr.md §8.
⚠️ `a.spr` holding under K-SB3 is the blindness filed on 2026-08-10 and
re-verified on 2026-09-05: it reads only the ERROR CODE, and a size that is
never applied raises nothing. `a.sprslot1` is the row built to cover it, and it
moved.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import knife_guard                                                # noqa: E402

SRC = os.path.join(ROOT, "basic", "graphics.asm")
WATCH = ("t.b0", "t.b1", "t.b2", "t.b3", "a.sprbad", "a.spr", "a.sprslot1")

# 🔴 EVERY CUT HERE IS THE SAME NUMBER OF BYTES AS WHAT IT REPLACES.
# Page 1 has 0 B free after this fix, so a cut that GROWS the code fails the
# build and leaves the previous ROM in place -- which is precisely the inert
# knife the ROM hash exists to catch, and the first draft hit it: `cp 255` is
# 2 B against `cp c`'s 1. `cp a` is the 1-byte way to say "the bound accepts
# everything" (Z set, CF clear, so `jp nc` is never taken).
# ⚠️ `_region` joins its lines WITHOUT a trailing newline, so an anchor
# ending in "\n" cannot match the region's LAST line -- which `ld c,2` is.
KNIVES = [
    ("K-SB1", "                cp      c\n",
     "                cp      a\n", "sea_bound"),
    ("K-SB2", "                ld      c,2                 ; serves both domains",
     "                ld      c,4                 ; serves both domains", "spr_extra_arg"),
    ("K-SB3", "                ret     z                   ; baud is validated and then IGNORED\n",
     "                ret     nz                  ; baud is validated and then IGNORED\n",
     "sea_bound"),
    ("K-SB4", "                dec     e                   ; baud 1..2 -> 0..1, so ONE bound test\n",
     "                nop                         ; baud 1..2 -> 0..1, so ONE bound test\n",
     "spr_extra_arg"),
]


ROW = None


def rows(log: str) -> dict[str, str]:
    """The reading is the QUOTED value after `zb=`, not the rest of the line --
    a row's deferral/control NOTE also lives there, and folding it into the
    value makes an unchanged row look changed the moment its note is edited."""
    import re as _re
    out = {}
    for ln in log.splitlines():
        m = _re.search(r"^\s*\S+\s+(\S+)\s+.*\bzb='([^']*)'", ln)
        if m and m.group(1) in WATCH:
            out[m.group(1)] = m.group(2)
    return out


def score(tag: str) -> dict[str, str]:
    p = subprocess.run(["make", "screenerr-acceptance"], cwd=ROOT,
                       capture_output=True, text=True)
    open(os.path.join(ROOT, "scratchpad", f"scrbaud_knife_{tag}.out"), "w").write(
        p.stdout + p.stderr)
    return rows(p.stdout)


def main() -> int:
    orig = open(SRC, encoding="utf-8").read()
    base_h = knife_guard.hashes()
    base = score("base")
    print(f"base ROM {base_h}")
    print("base rows:", base)
    bad = 0
    try:
        for tag, anchor, repl, routine in KNIVES:
            planted = knife_guard.cut(orig, anchor, repl, routine=routine)
            open(SRC, "w", encoding="utf-8").write(planted)
            moved, after, rc = knife_guard.build(f"scrbaud_{tag}", base_h)
            print(f"\n{tag}: {knife_guard.report(tag, moved, base_h, after)}")
            if not moved:
                # 🔴 THE FAILURE THIS GUARD EXISTS FOR: an inert cut reports
                # "0 rows moved", which is what a legitimately-covered arm
                # looks like [[a-knife-can-be-inert-because-the-build-did-not-happen]].
                print(f"  {tag} DID NOT REACH THE ROM -- score discarded")
                bad += 1
            else:
                got = score(tag)
                for w in WATCH:
                    if base.get(w) != got.get(w):
                        print(f"    {w}: {base.get(w)!r} -> {got.get(w)!r}  MOVED")
                    else:
                        print(f"    {w}: {base.get(w)!r}  held")
            open(SRC, "w", encoding="utf-8").write(orig)
    finally:
        open(SRC, "w", encoding="utf-8").write(orig)
        _m, restored, _rc = knife_guard.build("scrbaud_restore", base_h)
        ok = restored == base_h
        print(f"\nrestore: {base_h} -> {restored}  "
              f"{'BYTE-IDENTICAL' if ok else '🔴 DRIFT'}")
        bad += 0 if ok else 1
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
