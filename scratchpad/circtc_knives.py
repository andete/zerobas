#!/usr/bin/env python3
"""D-CIRCTC knives -- two size-neutral cuts, each with a predicted row set.

The fix DELETED cpt_asp_done's bespoke `cp ',' / jp z,cpt_err2` so a trailing
comma after a COMPLETE CIRCLE argument list is left for the resident's cp_done
`jp exec_stmt` boundary to reject AFTER the draw (draw-then-raise, matching both
references -- x.extra2 `2 5`). That REFUTES the seam classifier's "restructure,
second flag" verdict: it is a clean delete, like SWAP/PAINT/SPRITE.

A consequence the knives make visible: the tenant no longer distinguishes a
trailing comma from a clean end-of-list -- BOTH now flow through cpt_asp_done's
`jp cpt_finish`. So no circleparse.asm knife can move x.extra2 ALONE; the split
lives in the resident's exec_stmt now. K-CT1 shows exactly that (all three
aspect-present rows revert together). K-CT2 is the trap guard: it proves the
EMPTY aspect slot (x.extra) must still raise BEFORE drawing, so my fix correctly
left cpt_at_aspect's cpt_err2 in place.

Rules obeyed (zerobas-gate-operating-rules): cut a VALUE via a jp-retarget to a
label that keeps other incoming edges (deadcode-safe, size-neutral), `rm -rf
build` before every build, RESTORE BY WRITING THE BYTES, and assert WHICH image
moved -- a sub/*.asm cut moves sub.rom ONLY (basic-reloc.rom + merged UNCHANGED),
the opposite of the resident-side seam fixes.
"""
from __future__ import annotations

import atexit
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "sub/circleparse.asm"

BASE = {
    'c.colour': '24 4', 'c.start': '24 4', 'c.end': '24 4', 'c.aspect': '24 4',
    'k.colour': '24 4', 'k.start': '24 4', 'k.end': '24 4', 'k.aspect': '24 4',
    'o.none': '0 15', 'o.colour': '0 15', 'o.start': '0 5', 'o.end': '0 5',
    'x.extra': '2 4', 'x.extra2': '2 5', 'r.miss': '24 4', 'r.nocomma': '2 4',
    'c.ok': '0 5',
}

# cpt_asp_done's success exit (the ONLY unconditional `jp cpt_finish` in the file)
ASP_FINISH = "                jp      cpt_finish\n"
# cpt_at_aspect's "too many args" raiser (the ONLY `jp z,cpt_err2` left after the fix)
AT_ASP_ERR2 = ("                jp      z,cpt_err2          "
               "; too many args -> Syntax error\n")

KNIVES = [
    dict(name="K-CT1",
         what="cpt_asp_done `jp cpt_finish` -> `jp cpt_err2`: re-impose "
              "raise-before-draw on the WHOLE aspect-present path",
         old=ASP_FINISH,
         new="                jp      cpt_err2            ; K-CT1\n",
         # every row whose aspect is fully parsed reverts together -- the tenant
         # no longer tells a trailing comma from a clean completion.
         moves={'x.extra2': '2 4', 'c.ok': '2 4', 'o.end': '2 4'}),
    dict(name="K-CT2",
         what="cpt_at_aspect `jp z,cpt_err2` -> `jp z,cpt_finish`: send the "
              "EMPTY aspect slot to the delegate path (wrongly draws)",
         old=AT_ASP_ERR2,
         new="                jp      z,cpt_finish        ; K-CT2\n",
         moves={'x.extra': '2 5'}),
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
    assert sh("rm -rf build", f"scratchpad/ctknife_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/ctknife_{tag}_build.log")


def zb_faces(tag):
    log = f"scratchpad/ctknife_{tag}_probe.out"
    sh("python3 scratchpad/circmiss_probe.py --sides=zb", log)
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
    print(f"baseline {len(base_faces)} rows match circtc_after.out", flush=True)

    exact = 0
    for k in KNIVES:
        name = k["name"]
        open(SRC, "w").write(original.replace(k["old"], k["new"]))
        assert build(name) == 0, f"{name}: build failed -- see the log"
        h = hashes()
        assert h[1] != base_h[1], f"{name}: sub.rom did NOT move -- cut did not land"
        assert h[0] == base_h[0], f"{name}: basic-reloc.rom moved -- wrong image"
        assert h[2] == base_h[2], f"{name}: merged image moved -- wrong image"
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
        open(SRC, "w").write(original)          # RESTORE BY WRITING THE BYTES

    assert build("restore") == 0, "restore build failed"
    rh = hashes()
    print(f"\nrestored roms={' / '.join(rh)}", flush=True)
    assert rh == base_h, f"restore did not reproduce baseline: {rh} != {base_h}"
    print(f"{exact}/{len(KNIVES)} knife rows EXACT")
    return 0 if exact == len(KNIVES) else 1


if __name__ == "__main__":
    sys.exit(main())
