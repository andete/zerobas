#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PLAYOP knives — one per SITE, and two of them must redden GREEN rows.

The fix moves exactly two of `pl_syntax`'s four call sites to ERR 24. So there
are four knives and they are not the same kind:

  * K-PL1 / K-PL2 revert the two sites that moved. 🎯 EACH IS EXPECTED TO MOVE
    **TWO** ROWS, NOT ONE, because `pl_voice` is a LOOP: one instruction serves
    the first voice and every subsequent one. That is the claim TODO.md could
    not make, because it counted instructions rather than rows.
  * K-PL3 / K-PL4 point the two sites that must NOT move at the new target, on
    purpose. They redden rows that are green TODAY, which is the only way to
    show those rows can detect an over-wide fix -- the narrowness of "two of
    four" is otherwise unmeasured.

Rules obeyed (zerobas-gate-operating-rules): every cut retargets a jump whose
target keeps other incoming edges, `rm -rf build` before EVERY build, RESTORE BY
WRITING THE BYTES, and assert WHICH image moved -- play.asm is main-only, so
basic-reloc.rom MUST move and sub.rom MUST NOT.
"""
from __future__ import annotations

import atexit
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/play.asm"

BASE = {
    'p.bare': '24', 'p.colon': '24', 'p.comma': '2',
    'p.trail': '24', 'p.trailcolon': '24', 'p.dblcomma': '2',
    'p.four': '2', 'p.ok': '0', 'p.ok3': '0', 'p.empty': '0', 'p.num': '13',
}

KNIVES = [
    dict(name="K-PL1",
         what="the EOL site back to pl_syntax -- ERR 2, the pre-slice answer, "
              "at ONE of the two sites that moved",
         old="                jp      z,loc_missing       ; required slot ENDS here -> ERR 24",
         new="                jr      z,pl_syntax         ; K-PL1",
         # pl_voice is a LOOP, so this ONE instruction serves BOTH entry
         # conditions: the first voice AND every subsequent one.
         moves={'p.bare': '2', 'p.trail': '2'}),
    dict(name="K-PL2",
         what="the COLON site back to pl_syntax -- the OTHER site that moved, "
              "and its own two rows",
         old="                jp      z,loc_missing       ; `PLAY:` likewise -> ERR 24",
         new="                jr      z,pl_syntax         ; K-PL2",
         moves={'p.colon': '2', 'p.trailcolon': '2'}),
    dict(name="K-PL3",
         what="the COMMA site to loc_missing -- the site the measurement says "
              "must NOT move, moved on purpose",
         old="                jr      z,pl_syntax         ; bare comma (PLAY ,\"E\") -> Syntax error,",
         new="                jp      z,loc_missing       ; K-PL3",
         moves={'p.comma': '24', 'p.dblcomma': '24'}),
    dict(name="K-PL4",
         what="the 4th-voice site to loc_missing -- the one TODO.md marked "
              "UNMEASURED and which the measurement says is already right",
         # Space plan B-1 (GA-CROSS-ROMSCAN, 2026-10-04) folded `jr nc,pl_syntax /
         # jr pl_voice` into `jr c,pl_voice` + fallthrough, so the knife now plants a
         # `jp loc_missing` on that fallthrough -- the same cut, the new shape.
         old="                jr      c,pl_voice          ; a 4th voice string falls into Syntax error",
         new="                jr      c,pl_voice          ; K-PL4\n                jp      loc_missing",
         moves={'p.four': '24'}),
]

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def build(tag):
    assert sh("rm -rf build", f"scratchpad/plknife_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/plknife_{tag}_build.log")


def zb_faces(tag):
    log = f"scratchpad/plknife_{tag}_probe.out"
    sh("python3 scratchpad/playop_probe.py --sides=zb", log)
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
    assert not bad, f"baseline does not match playop_after.out: {bad}"
    print(f"baseline {len(base_faces)} rows match playop_after.out", flush=True)

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
