#!/usr/bin/env python3
"""D-CLRFIX knives -- four cuts, each separating ONE claim of a two-part fix.

The fix has two independent halves and they close DIFFERENT rows:

  (a) the CARVE -- deleting ex_clear's `cp ',' / jr z,clr_himem` -- closes the
      LEADING-comma rows, because the leading comma then reaches the POOL
      argument's eval_int16_checked, which already had a guard;
  (b) the SWAP -- clr_himem's `call eval` -> `call eval_int16_checked` -- closes
      the TRAILING-comma rows and every other fault code the HIMEM slot carried.

🎯 A differential cannot tell those apart: both halves landed in one commit and
every row went green. K-CF1 reverts (b) alone and K-CF2 restores (a) alone, and
the two predicted row sets are DISJOINT. That is the claim "these are two fixes,
not one", measured.

K-CF3 is the control knife in the D-PAINTMISS K-PM1/K-PM2 sense: it narrows the
new coercion from int16 to a byte, which is WRONG (`CLEAR 200,&H9000` is
accepted on all three machines) and reddens exactly the rows that say so.
🔴 It is also predicted to turn `z.neg` GREEN -- the one row this slice does NOT
fix -- for entirely the wrong reason. A knife that makes a red row agree is the
sharpest possible demonstration of [[a-case-that-agrees-can-agree-for-the-wrong-reason]].

K-CF4 cuts the `inc hl` that consumes the comma, so every row that reaches
clr_himem answers ERR 2 whatever it was going to answer.

🔴 ROUND 1 SCORED 2/4, AND BOTH MISSES WERE ONE OMISSION -- MINE, NOT THE
MACHINE'S. K-CF3 and K-CF4 each stop `CLEAR 200,-1` reaching the store, so
`h.neg` goes `->65535` -> `SAME` along with `z.neg`. Every other ERR row in this
file is predicted together with its HIMEM twin; the ONE row I omitted the twin
for is the one row this slice does not fix, which I had mentally filed as "out
of scope, ignore". 🎯 A row written off as out of scope drops out of the
BOOKKEEPING while staying in the DENOMINATOR. The `moves` sets below are
corrected; `scratchpad/clrfix_knives_round1.out` is kept as the record.

Rules obeyed: cut a VALUE not a call, `rm -rf build` before EVERY knife build,
RESTORE BY WRITING THE BYTES, and assert WHICH image moved -- a `basic/*.asm`
edit moves basic-reloc.rom AND the merged image and NOT sub.rom.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
CLEAR = "basic/clear.asm"

BASE = {
    'q.trail': '24 0',
    'q.kcolon': '24 0',
    'q.comma': '2 0',
    'q.commak': '2 0',
    'q.conly': '2 0',
    'q.div': '11 0',
    'q.str': '13 0',
    'q.ovf': '6 0',
    'q.ok': '0 0',
    'q.both': '0 0',
    'q.bare': '0 0',
    'q.kbare': '0 0',
    'z.hd000': '2 0',
    'z.seq': 'UNTRAPPED Syntax error in 30',
    'z.neg': '0 0',
    't.notrap': '11 0',
    'h.none': 'SAME',
    'h.ok': 'SAME',
    'h.set': '->36864',
    'h.trail': 'SAME',
    'h.comma': 'SAME',
    'h.div': 'SAME',
    'h.str': 'SAME',
    'h.ovf': 'SAME',
    'h.hd000': 'SAME',
    'h.neg': '->65535',
}

SWAP = "                call    eval_int16_checked  ; DE = int16, or aborts (ERR 2/6/11/13)\n"
INCHL = "                inc     hl                  ; past the comma\n"
CARVE_ANCHOR = """                cp      COLON
                jr      z,clr_done          ; bare CLEAR before ':'
"""

KNIVES = [
    dict(name="K-CF1", src=CLEAR,
         what="clr_himem's `call eval_int16_checked` -> `call eval`: half (b) "
              "reverted alone, so the HIMEM slot is unguarded again while the "
              "carve stays in",
         old=SWAP,
         new="                call    eval                ; K-CF1\n",
         moves={'q.trail': 'UNTRAPPED Missing operand in 30',
                'q.kcolon': 'UNTRAPPED Missing operand in 30',
                'q.div': 'UNTRAPPED Division by zero in 30',
                'q.str': 'UNTRAPPED Type mismatch in 30',
                'q.ovf': '0 0',
                'h.trail': '->0', 'h.div': '->0', 'h.str': '->0',
                'h.ovf': '->0'}),
    dict(name="K-CF2", src=CLEAR,
         what="ex_clear's deleted leading-comma arm RESTORED (+4 B): half (a) "
              "undone alone, so `CLEAR ,himem` is accepted again while the "
              "HIMEM slot keeps its new guard",
         old=CARVE_ANCHOR,
         new=CARVE_ANCHOR + "                cp      ','                 ; K-CF2\n"
                            "                jr      z,clr_himem\n",
         moves={'q.comma': '0 0',
                'q.commak': 'UNTRAPPED Out of memory in 30',
                'q.conly': '24 0',
                'z.hd000': '0 0', 'z.seq': '0 0',
                'h.comma': '->200', 'h.hd000': '->53248'}),
    dict(name="K-CF3", src=CLEAR,
         what="the new coercion narrowed from int16 to a BYTE -- wrong, because "
              "`CLEAR 200,&H9000` is accepted on all three machines",
         old=SWAP,
         new="                call    eval_byte_checked   ; K-CF3\n",
         moves={'q.both': '5 0', 'h.set': 'SAME',
                # 🔴 ROUND 1 OMITTED h.neg. The byte narrowing rejects -1,
                # so the negative case stops reaching the store and BOTH of
                # the slice's surviving red rows go GREEN under this knife --
                # for entirely the wrong reason.
                'z.neg': '5 0', 'h.neg': 'SAME'}),
    dict(name="K-CF4", src=CLEAR,
         what="clr_himem's `inc hl` -> `nop`: the comma is no longer consumed, "
              "so eval sees it as an empty operand and EVERY row that reaches "
              "the slot answers ERR 2",
         old=INCHL,
         new="                nop                         ; K-CF4\n",
         moves={'q.trail': '2 0', 'q.kcolon': '2 0', 'q.div': '2 0',
                'q.str': '2 0', 'q.ovf': '2 0', 'q.both': '2 0',
                'h.set': 'SAME',
                # 🔴 ROUND 1 OMITTED h.neg here too, for the same reason.
                'z.neg': '2 0', 'h.neg': 'SAME'}),
]

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def build(tag):
    assert sh("rm -rf build", f"scratchpad/cfknife_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/cfknife_{tag}_build.log")


def zb_faces(tag):
    """BOTH probes: the ERR fence AND the HIMEM write-back, merged."""
    faces = {}
    for script, suffix in (("clrfix_probe.py", "err"), ("clrfix_himem.py", "him")):
        log = f"scratchpad/cfknife_{tag}_{suffix}.out"
        sh(f"python3 scratchpad/{script} --sides=zb", log)
        for line in open(log):
            if line.startswith("  ran zb "):
                parts = line.split(None, 3)
                faces[parts[2]] = parts[3].strip().strip("'")
    return faces


def main():
    originals = {CLEAR: open(CLEAR).read()}
    for k in KNIVES:
        assert originals[k["src"]].count(k["old"]) == 1, f"{k['name']}: anchor not unique"

    print("=== baseline ===", flush=True)
    assert build("base") == 0, "baseline build failed"
    base_h = hashes()
    print("baseline roms=" + " / ".join(base_h), flush=True)
    base_faces = zb_faces("base")
    assert set(base_faces) == set(BASE), (
        f"row set mismatch: missing {sorted(set(BASE) - set(base_faces))}, "
        f"extra {sorted(set(base_faces) - set(BASE))}")
    for row, want in BASE.items():
        assert base_faces[row] == want, \
            f"baseline row {row}: {base_faces[row]!r} != documented {want!r}"
    print(f"baseline {len(base_faces)} rows match the after-run", flush=True)

    exact = 0
    for k in KNIVES:
        name, src = k["name"], k["src"]
        open(src, "w").write(originals[src].replace(k["old"], k["new"]))
        assert build(name) == 0, f"{name}: build failed -- see the log"
        h = hashes()
        assert h[0] != base_h[0], f"{name}: basic-reloc.rom did NOT move -- the cut did not land"
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
            print("  NOT EXACT: "
                  + ", ".join(f"{r} got {g!r} want {w!r}" for r, (g, w) in sorted(bad.items())),
                  flush=True)
        else:
            exact += 1
            print(f"  EXACT -- {len(k['moves'])} predicted, {len(moved)} moved", flush=True)
        open(src, "w").write(originals[src])      # RESTORE BY WRITING THE BYTES

    assert build("restore") == 0, "restore build failed"
    rh = hashes()
    print(f"\nrestored roms={' / '.join(rh)}", flush=True)
    assert rh == base_h, f"restore did not reproduce the baseline: {rh} != {base_h}"
    print(f"{exact}/{len(KNIVES)} knife rows EXACT")
    return 0 if exact == len(KNIVES) else 1


if __name__ == "__main__":
    sys.exit(main())
