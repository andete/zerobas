#!/usr/bin/env python3
"""D-CIRCMISS knives -- four size-neutral cuts, each with a predicted row set.

Every knife obeys the tree's rules: it cuts a VALUE (never a call -- a deleted
call fails `make deadcode` and builds no ROM), it is preceded by `rm -rf build`,
it RESTORES BY WRITING THE BYTES (never shutil.copy2 -- mtime preservation makes
make rebuild nothing and the next gate reads the knifed ROM), and it asserts
WHICH image moved.

⚠️ THE SIGNATURE HERE IS THE OPPOSITE OF D-MISSOPFIX'S. This is a `sub/*.asm`
edit, so `sub.rom` must MOVE and `basic-reloc.rom` + the merged image must NOT.
D-FNEXPR2's K-F2-4 halted with the right verdict and the wrong reason for
exactly this confusion, so the assertion names the expectation per knife.

The two narrowness knives are the point of the slice. The design question was
never "does ERR 24 come out" -- it was "does the fix leave the LEGITIMATE
omitted slot alone". K-CM3 and K-CM4 point one legitimate exit each at the new
raiser and predict that exactly one `o.*` row reddens, which is what makes those
four green rows detectors rather than decoration.
"""
from __future__ import annotations

import atexit
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
SRC = "sub/circleparse.asm"

# ---------------------------------------------------------------------------
# the post-fix zerobas baseline (scratchpad/circmiss_after.out) and, for each
# knife, ONLY the rows predicted to move away from it.
# ---------------------------------------------------------------------------
BASE = {
    'c.colour': '24 4', 'c.start': '24 4', 'c.end': '24 4', 'c.aspect': '24 4',
    'k.colour': '24 4', 'k.start': '24 4', 'k.end': '24 4', 'k.aspect': '24 4',
    'o.none': '0 15', 'o.colour': '0 15', 'o.start': '0 5', 'o.end': '0 5',
    'x.extra': '2 4', 'x.extra2': '2 4', 'r.miss': '24 4', 'r.nocomma': '2 4',
    'c.ok': '0 5',
}

ERR24 = "cpt_err24:\n                ld      a,24\n"
STARTINTRO = "                jp      z,cpt_start_intro   ; c omitted; this comma also intros start\n"
NOOPT = "                jp      nz,cpt_finish       ; no optional fields -> draw\n"

KNIVES = [
    dict(name="K-CM1",
         what="cpt_err24 `ld a,24` -> `ld a,0` (GFX_RES=0 is 'no error', so the "
              "resident draws) -- the bug, re-created",
         old=ERR24, new="cpt_err24:\n                ld      a,0\n",
         moves={'c.colour': '0 15', 'c.start': '0 5', 'c.end': '0 5',
                'c.aspect': '0 5', 'k.colour': '0 15', 'k.start': '0 5',
                'k.end': '0 5', 'k.aspect': '0 5'}),
    dict(name="K-CM2",
         what="cpt_err24 `ld a,24` -> `ld a,5` -- WRONG CODE, and the prediction "
              "is that the PICTURE is still protected (R stays 4)",
         old=ERR24, new="cpt_err24:\n                ld      a,5\n",
         moves={k: '5 4' for k in ('c.colour', 'c.start', 'c.end', 'c.aspect',
                                   'k.colour', 'k.start', 'k.end', 'k.aspect')}),
    dict(name="K-CM3",
         what="cpt_at_c's `jp z,cpt_start_intro` -> `jp z,cpt_err24`: the "
              "LEGITIMATE omitted colour is sent to the new raiser",
         old=STARTINTRO,
         new="                jp      z,cpt_err24         ; K-CM3\n",
         moves={'o.colour': '24 4'}),
    dict(name="K-CM4",
         what="cpt_after_r's `jp nz,cpt_finish` -> `jp nz,cpt_err24`: the "
              "no-optional-fields exit is sent to the new raiser",
         old=NOOPT,
         new="                jp      nz,cpt_err24        ; K-CM4\n",
         moves={'o.none': '24 4'}),
]

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def hashes():
    out = []
    for p in IMAGES:
        out.append(hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
                   if os.path.exists(p) else "ABSENT")
    return out


def build(tag):
    assert sh("rm -rf build", f"scratchpad/knife_{tag}_rm.log") == 0
    rc = sh("make repack-machine", f"scratchpad/knife_{tag}_build.log")
    return rc


def zb_faces(tag):
    log = f"scratchpad/knife_{tag}_probe.out"
    rc = sh("python3 scratchpad/circmiss_probe.py --sides=zb", log)
    faces = {}
    for line in open(log):
        if line.startswith("  ran zb "):
            parts = line.split(None, 3)
            faces[parts[2]] = parts[3].strip().strip("'")
    return rc, faces


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
    rc, base_faces = zb_faces("base")
    for row, want in BASE.items():
        got = base_faces.get(row)
        assert got == want, f"baseline row {row}: {got!r} != documented {want!r}"
    print(f"baseline {len(base_faces)} rows match scratchpad/circmiss_after.out",
          flush=True)

    exact = 0
    for k in KNIVES:
        name = k["name"]
        open(SRC, "w").write(original.replace(k["old"], k["new"]))
        assert build(name) == 0, f"{name}: build failed -- see the log"
        h = hashes()
        # a sub/*.asm cut moves sub.rom ONLY.
        assert h[1] != base_h[1], f"{name}: sub.rom did NOT move -- the cut did not land"
        assert h[0] == base_h[0], f"{name}: basic-reloc.rom moved -- wrong image"
        assert h[2] == base_h[2], f"{name}: merged image moved -- wrong image"
        print(f"\n{name}  roms={' / '.join(h)}", flush=True)
        print(f"  cut: {k['what']}", flush=True)
        rc, faces = zb_faces(name)
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
    print(f"{exact}/{len(KNIVES)} knife rows EXACT")
    return 0 if exact == len(KNIVES) else 1


if __name__ == "__main__":
    sys.exit(main())
