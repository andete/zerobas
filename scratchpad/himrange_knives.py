#!/usr/bin/env python3
"""D-HIMRANGE knives -- four size-neutral VALUE cuts, one per sub-rule of the
CLEAR memory-ceiling range check (basic/clear.asm clr_himem).

Each knife perturbs exactly one constant/condition and predicts exactly which
rows change, so a green differential is not believed until each band's detector
reddens the rows it guards.

  K-HR1  jr nz,clr_h_store -> jr clr_h_store : the range check is bypassed
         entirely -- THE PRE-FIX BUILD re-created. Predictions are MEASURED off
         scratchpad/himrange_probe.out (the real pre-fix run), not reasoned, so
         it is also a standing regression detector for this whole slice.
  K-HR2  ld hl,CLR_HIMEM_TOP -> ld hl,$FFFF : the upper edge ($F380) removed, so
         everything up to 65535 is accepted. Only the > $F380 rows move.
  K-HR3  ld hl,(PRGEND) -> ld hl,0 : the floor drops to POOLSIZE+MARGIN (=880),
         so every in-RAM ERR-7 row is accepted. Only the ERR-7 rows move.
  K-HR4  ld hl,$7FFF -> ld hl,0 : the low ERR-5 edge collapses to "value==0", so
         a value in (0,$8000) is no longer ERR 5 -- it falls to the floor check
         and becomes ERR 7. d.zero (==0) stays ERR 5: the control that proves the
         cut landed where I think.

Rules obeyed: size-neutral value cuts (jr-cond / ld-hl-immediate, 2/3 bytes both
ways), `rm -rf build` before EVERY build, RESTORE BY WRITING THE BYTES, assert
WHICH image moved (a basic/clear.asm edit moves basic-reloc.rom AND the merged
image, NOT sub.rom), and invoke the SUBJECT (repack-machine), not a gate target.
"""
from __future__ import annotations

import atexit
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/clear.asm"
FILTER = "d.,u.6,l.33,l.34,f.336,f.337,b.7,b.8"

# baseline zb faces on the FIXED build (scratchpad/himrange_verify.out).
BASE = {
    'd.50000': '0 ->50000', 'd.40000': '0 ->40000', 'd.32768': '7 SAME',
    'd.32767': '5 SAME',    'd.65535': '5 SAME',    'd.65536': '6 SAME',
    'd.70000': '6 SAME',    'd.hffff': '5 SAME',    'd.neg1':  '5 SAME',
    'd.h8000': '7 SAME',    'd.hd000': '0 ->53248', 'd.zero':  '5 SAME',
    'd.one':   '5 SAME',    'd.h4000': '5 SAME',    'd.h8050': '7 SAME',
    'u.62337': '5 SAME',    'u.63000': '5 SAME',    'l.33000': '7 SAME',
    'l.34000': '0 ->34000', 'f.33650': '7 SAME',    'f.33700': '7 SAME',
    'f.33750': '0 ->33750', 'b.7fff':  '5 SAME',    'b.8001':  '7 SAME',
}

# pre-fix accept faces (scratchpad/himrange_probe.out), for K-HR1.
PREFIX = {
    'd.32768': '0 ->32768', 'd.32767': '0 ->32767', 'd.65535': '0 ->65535',
    'd.hffff': '0 ->65535', 'd.neg1':  '0 ->65535', 'd.h8000': '0 ->32768',
    'd.zero':  '0 ->0',     'd.one':   '0 ->1',     'd.h4000': '0 ->16384',
    'd.h8050': '0 ->32848', 'u.62337': '0 ->62337', 'u.63000': '0 ->63000',
    'l.33000': '0 ->33000', 'f.33650': '0 ->33650', 'f.33700': '0 ->33700',
    'b.7fff':  '0 ->32767', 'b.8001':  '0 ->32769',
}

KNIVES = [
    dict(name="K-HR1",
         what="range check bypassed (jr nz -> jr): the PRE-FIX build, faces "
              "read off scratchpad/himrange_probe.out",
         old="jr      nz,clr_h_store", new="jr      clr_h_store   ",
         moves=PREFIX),
    dict(name="K-HR2",
         what="upper edge removed (CLR_HIMEM_TOP -> $FFFF): only > $F380 rows move",
         old="ld      hl,CLR_HIMEM_TOP", new="ld      hl,$FFFF        ",
         moves={'d.65535': '0 ->65535', 'd.hffff': '0 ->65535',
                'd.neg1': '0 ->65535', 'u.62337': '0 ->62337',
                'u.63000': '0 ->63000'}),
    dict(name="K-HR3",
         what="floor dropped (PRGEND -> 0): every in-RAM ERR-7 row is accepted",
         old="ld      hl,(PRGEND)", new="ld      hl,0        ",
         moves={'d.32768': '0 ->32768', 'd.h8000': '0 ->32768',
                'd.h8050': '0 ->32848', 'l.33000': '0 ->33000',
                'f.33650': '0 ->33650', 'f.33700': '0 ->33700',
                'b.8001': '0 ->32769'}),
    dict(name="K-HR4",
         what="low ERR-5 edge collapsed ($7FFF -> 0): (0,$8000) becomes ERR 7, "
              "d.zero (==0) stays ERR 5 as the control",
         old="ld      hl,$7FFF", new="ld      hl,0    ",
         moves={'d.one': '7 SAME', 'd.h4000': '7 SAME',
                'b.7fff': '7 SAME', 'd.32767': '7 SAME'}),
]

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def build(tag):
    assert sh("rm -rf build", f"scratchpad/hrknife_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/hrknife_{tag}_build.log")


def zb_faces(tag):
    log = f"scratchpad/hrknife_{tag}_probe.out"
    sh(f'python3 scratchpad/himdom_probe.py "{FILTER}" --sides=zb', log)
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
        assert original.count(k["old"]) == 1, \
            f"{k['name']}: anchor {k['old']!r} count={original.count(k['old'])}"

    print("=== baseline ===", flush=True)
    assert build("base") == 0, "baseline build failed"
    base_h = hashes()
    print("baseline roms=" + " / ".join(base_h), flush=True)
    base_faces = zb_faces("base")
    miss = {r: (base_faces.get(r), w) for r, w in BASE.items()
            if base_faces.get(r) != w}
    assert not miss, f"baseline mismatch: {miss}"
    print(f"baseline {len(BASE)} rows match himrange_verify.out", flush=True)

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
            print("  NOT EXACT: "
                  + ", ".join(f"{r} got {g!r} want {w!r}"
                              for r, (g, w) in sorted(bad.items())), flush=True)
        else:
            exact += 1
            print(f"  EXACT -- {len(k['moves'])} predicted, {len(moved)} moved",
                  flush=True)
        open(SRC, "w").write(original)          # RESTORE BY WRITING THE BYTES

    assert build("restore") == 0, "restore build failed"
    rh = hashes()
    print(f"\nrestored roms={' / '.join(rh)}", flush=True)
    assert rh == base_h, f"restore did not reproduce the baseline: {rh} != {base_h}"
    print(f"\n{exact}/{len(KNIVES)} knives EXACT")
    return 0 if exact == len(KNIVES) else 1


if __name__ == "__main__":
    sys.exit(main())
