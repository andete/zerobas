#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EVFERR knives -- five size-neutral jp-retargets, each with a row set.

The fix is five instructions whose TARGET changed and nothing else, so every
knife is the same shape: point one of them somewhere wrong and name, in advance,
exactly which rows move. Three claims are under test and they are different:

  * K-EV1/K-EV3/K-EV4 test that a site is LOAD-BEARING -- revert it and its own
    rows go back to COMPLETING SILENTLY (0).
  * K-EV3 and K-EV4 together test NARROWNESS, the trap this whole item sprang
    on D-MISSOPFIX: the two VARPTR sites are separate decisions, so reverting
    one must move ONE row. 🎯 And neither moves `v.nopar`/`v.badarg`, which is
    the point: those rows answer 2 through exec_stmt's leftover-token layer
    whatever the expression layer does. A knife that reddened them would mean
    the separator rows were not separating.
  * K-EV2/K-EV5 test the CODE, not the site: retarget to a WRONG-but-deferring
    label (ev_f_missop = 24, ev_f_empty = 2) and the rows must read that other
    code. Without these, "ev_f_empty" and "ev_f_ifc" are two rules that coincide
    on every row that merely ABORTS.

Rules obeyed (zerobas-gate-operating-rules): retarget a `jp` whose target keeps
other incoming edges (deadcode-safe, size-neutral -- a knife that orphans a
label cannot be built), `rm -rf build` before EVERY build, RESTORE BY WRITING
THE BYTES, and assert WHICH image moved: expr.asm is main-only, so
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
SRC = "basic/expr.asm"

# The shipping faces, from scratchpad/evferr_after.out (zb column).
BASE = {
    'p.noclose': '2', 'p.colon': '2', 'p.nested': '2', 'p.print': '2',
    'p.ok': '0', 'p.if': '2', 'p.for': '2',
    'v.nopar': '2', 'v.nopareol': '2', 'v.badarg': '2', 'v.badargeol': '2',
    'v.noclose': '2', 'v.nocloseset': '2', 'v.ok': '0', 'v.aryunset': '2',
    'e.eofdev': '59', 'e.eofcrt': '5', 'e.lofcrt': '5', 'e.crtok': '0',
    's.strparen': '2', 's.strvp': '2', 's.strok': '13',
    'b.nopar': '2', 'b.nopareol': '2', 'b.openeol': '24', 'b.ok': '0',
    'd.arybadsub': '9', 'd.arybadsubok': '9',
    'd.strunset': '2', 'd.strunsetok': '5',
}

PAREN_ROWS = ['p.noclose', 'p.colon', 'p.nested', 'p.print', 'p.if', 'p.for']

# (1-based line, the exact line that must be there, the replacement)
KNIVES = [
    dict(name="K-EV1", line=835,
         what="ev_f_paren's close check back to the SILENT ev_f_err -- "
              "re-creates the pre-slice defect at its own site",
         old="                jp      nz,ev_f_empty",
         new="                jp      nz,ev_f_err         ; K-EV1",
         moves={r: '0' for r in PAREN_ROWS}),
    dict(name="K-EV2", line=835,
         what="ev_f_paren's close check to ev_f_missop -- the right SITE with "
              "the wrong CODE (24 instead of 2)",
         old="                jp      nz,ev_f_empty",
         new="                jp      nz,ev_f_missop      ; K-EV2",
         moves={r: '24' for r in PAREN_ROWS}),
    dict(name="K-EV3", line=1928,
         what="VARPTR's missing-'(' check back to ev_f_err -- ONE of the two "
              "VARPTR sites, so ONE row",
         old="                jp      nz,ev_f_empty",
         new="                jp      nz,ev_f_err         ; K-EV3",
         moves={'v.nopareol': '0'}),
    dict(name="K-EV4", line=1932,
         what="VARPTR's not-a-name check back to ev_f_err -- the OTHER site, "
              "the other row",
         old="                jp      nc,ev_f_empty",
         new="                jp      nc,ev_f_err         ; K-EV4",
         moves={'v.badargeol': '0'}),
    dict(name="K-EV5", line=1135,
         what="EOF's length-less-channel check to ev_f_empty -- a DEFERRED "
              "error either way, but Syntax (2) instead of the measured 5",
         old="                jp      nc,ev_f_ifc         ; -> function error "
             "(never fch_select them)",
         new="                jp      nc,ev_f_empty       ; K-EV5",
         moves={'e.eofcrt': '2'}),
    dict(name="K-EV6", line=None, anchor=(
        "                call    ev_sp\n"
        "                cp      ')'\n"
        "                jp      nz,ev_f_empty       ; malformed close ->"
        " Syntax error (2)\n"
        "                ld      e,3\n"
        "                jp      ev_f_defer"),
         what="vptr_unset back to raising its domain error FIRST -- the "
              "pre-slice ordering, restored by DELETING the close check",
         replacement=("                ld      e,3          ; K-EV6\n"
                      "                jp      ev_f_defer"),
         moves={'v.noclose': '5', 'd.strunset': '5'}),
]

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def build(tag):
    assert sh("rm -rf build", f"scratchpad/evknife_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/evknife_{tag}_build.log")


def zb_faces(tag):
    log = f"scratchpad/evknife_{tag}_probe.out"
    sh("python3 scratchpad/evferr_probe.py --sides=zb", log)
    faces = {}
    for line in open(log):
        if line.startswith("  ran zb "):
            p = line.split(None, 3)
            faces[p[2]] = p[3].split("->", 1)[1].strip().strip("'")
    return faces


def cut(text, k):
    if k["line"] is None:                   # text-anchored knife (multi-line)
        assert text.count(k["anchor"]) == 1, (
            f"{k['name']}: anchor is not unique ({text.count(k['anchor'])})")
        return text.replace(k["anchor"], k["replacement"], 1)
    lines = text.split("\n")
    got = lines[k["line"] - 1]
    assert got == k["old"], (f"{k['name']}: line {k['line']} is {got!r}, "
                             f"not the expected {k['old']!r}")
    lines[k["line"] - 1] = k["new"]
    return "\n".join(lines)


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
        cut(original, k)                    # anchor check, before anything builds

    print("=== baseline ===", flush=True)
    assert build("base") == 0, "baseline build failed"
    base_h = hashes()
    print("baseline roms=" + " / ".join(base_h), flush=True)
    base_faces = zb_faces("base")
    bad = {r: (base_faces.get(r), w) for r, w in BASE.items()
           if base_faces.get(r) != w}
    assert not bad, f"baseline does not match evferr_after.out: {bad}"
    print(f"baseline {len(base_faces)} rows match evferr_after.out", flush=True)

    exact = 0
    for k in KNIVES:
        name = k["name"]
        open(SRC, "w").write(cut(original, k))
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
