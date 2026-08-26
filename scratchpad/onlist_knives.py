#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ONLIST knives — one cut for the fix, and THREE for the rule I nearly shipped.

The fix raises `Syntax error` at exactly ONE of `eon_seek_nth`'s seven jump
sites: `esn_p1`'s `cp LINENO_TOKEN`, and only when DE==1 (the position being
sought). My source reading said FOUR of the seven were errors. The measurement
said one, and the other three are rows where zerobas was ALREADY CORRECT.

So the knives are asymmetric on purpose:

  * K-OL1 is the ordinary one: revert the discriminator and the three fixed rows
    go back to completing silently.
  * K-OL2 makes the test UNCONDITIONAL — the "any missing entry is an error"
    rule — which is the first thing a reader of the source would write.
  * K-OL3 and K-OL4 point the OTHER malformed-looking sites at the raiser, one
    each: `esn_ok`'s "malformed: stop here" and `esn_scan`'s "no entries at all".

🎯 K-OL2/3/4 EACH RE-CREATE A SPECIFIC REGRESSION THE REFUTED WIDE RULE WOULD
HAVE SHIPPED, and each must redden rows that are green TODAY. A knife that
reddens nothing there would mean those rows cannot detect the over-wide fix —
i.e. that the narrowness of this slice is unmeasured, which is the whole claim.

Rules obeyed (zerobas-gate-operating-rules): every cut retargets a `jr`/`jp`
whose target keeps other incoming edges, `rm -rf build` before EVERY build,
RESTORE BY WRITING THE BYTES, and assert WHICH image moved — program.asm is
main-only, so basic-reloc.rom MUST move and sub.rom MUST NOT.
"""
from __future__ import annotations

import atexit
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/program.asm"

BASE = {
    'o.nolist': '2 0', 'o.nolistsub': '2 0', 'o.zeronolist': '0 1',
    'o.overnolist': '0 1', 'o.short': '0 1', 'o.zero': '0 1',
    'o.trail1': '0 2', 'o.trail0': '0 1', 'o.badafter': '0 2',
    'o.n2trail': '2 0', 'o.n5trail': '0 1', 'o.n2short': '0 1',
    'o.n2ok': '0 2', 'o.ok': '0 2', 'o.gosubok': '0 2',
}

KNIVES = [
    dict(name="K-OL1",
         what="esn_p1's jump back to esn_nocf: delete the discriminator, "
              "restoring the pre-slice silence",
         old="                jr      nz,esn_notlineno    ; D-ONLIST: NOT simply \"list shorter",
         new="                jr      nz,esn_nocf         ; K-OL1: NOT simply \"list shorter",
         moves={'o.nolist': '0 1', 'o.nolistsub': '0 1', 'o.n2trail': '0 1'}),
    dict(name="K-OL2",
         what="force the discriminator ALWAYS-TRUE (`or e` -> `xor a`) -- the "
              "'any missing entry is an error' rule, i.e. the refuted wide one",
         old=("                dec     de\n"
              "                ld      a,d\n"
              "                or      e\n"
              "                jr      nz,esn_nocf         ; still counting"),
         new=("                dec     de\n"
              "                ld      a,d\n"
              "                xor     a                   ; K-OL2\n"
              "                jr      nz,esn_nocf         ; still counting"),
         # ONLY the rows that reach esn_p1's cp $0E failure can move; `ON 5 GOTO
         # 40` and `ON 2 GOTO 40` fail at the `cp ','` site instead and cannot.
         moves={'o.overnolist': '2 0', 'o.n5trail': '2 0'}),
    dict(name="K-OL3",
         what="esn_ok's \"malformed: stop here\" pointed at the raiser -- the "
              "wide rule's second regression",
         old="                jr      nz,esn_ok           ; malformed: stop here",
         new="                jr      nz,esn_bad          ; K-OL3",
         moves={'o.trail1': '2 0', 'o.badafter': '2 0'}),
    dict(name="K-OL4",
         what="esn_scan's \"no entries at all\" pointed at the raiser -- the "
              "wide rule's third regression (the N=0 path)",
         old="                jr      nz,esn_nocf         ; no entries at all",
         new="                jr      nz,esn_bad          ; K-OL4",
         moves={'o.zeronolist': '2 0'}),
]

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def build(tag):
    assert sh("rm -rf build", f"scratchpad/olknife_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/olknife_{tag}_build.log")


def zb_faces(tag):
    log = f"scratchpad/olknife_{tag}_probe.out"
    sh("python3 scratchpad/onlist_probe.py --sides=zb", log)
    faces = {}
    for line in open(log):
        if line.startswith("  ran zb "):
            p = line.split(None, 3)
            faces[p[2]] = p[3].split("->", 1)[1].strip().strip("'")
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
        n = original.count(k["old"])
        assert n == 1, f"{k['name']}: anchor appears {n} times"

    print("=== baseline ===", flush=True)
    assert build("base") == 0, "baseline build failed"
    base_h = hashes()
    print("baseline roms=" + " / ".join(base_h), flush=True)
    base_faces = zb_faces("base")
    bad = {r: (base_faces.get(r), w) for r, w in BASE.items()
           if base_faces.get(r) != w}
    assert not bad, f"baseline does not match onlist_after.out: {bad}"
    print(f"baseline {len(base_faces)} rows match onlist_after.out", flush=True)

    exact = 0
    for k in KNIVES:
        name = k["name"]
        open(SRC, "w").write(original.replace(k["old"], k["new"], 1))
        assert build(name) == 0, f"{name}: build failed -- see the log"
        h = hashes()
        assert h[0] != base_h[0], f"{name}: basic-reloc.rom did NOT move -- no cut"
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
