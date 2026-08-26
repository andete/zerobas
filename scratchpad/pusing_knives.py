#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PUSING knives — one per RULE, because the slice replaced two answers with five.

The head used to give ERR 2 for everything malformed and complete silently for
two shapes. It now distinguishes five cases, so each knife re-merges ONE of the
distinctions and names the rows that collapse:

  K-PU1  missing format        -> the field-less raiser (24 becomes 5)
  K-PU2  non-string format     -> stmt_error            (13 becomes 2, pre-slice)
  K-PU3  ',' accepted again    -> the separator the references reject
  K-PU4  field-less format     -> loc_missing           (5 becomes 24)
  K-PU5  ';' with no values    -> pu_main               (restores the SILENCE)

🎯 K-PU5 IS THE ONE THAT MATTERS MOST: it re-creates the silent completion that
opened this slice. A knife that could not restore the original defect would mean
the row reporting it is not the row the fix serves.

⚠️ K-PU3 has to INTRODUCE its own landing label, because the point of the cut is
to stop rejecting and there is no existing non-error target here. Its first
draft jumped to a name that did not exist -- a knife that cannot assemble is not
a lenient knife, it is no knife.

Rules obeyed (zerobas-gate-operating-rules): `rm -rf build` before EVERY build,
RESTORE BY WRITING THE BYTES, and assert WHICH image moved -- printusing.asm is
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
SRC = "basic/printusing.asm"

BASE = {
    'u.none': '24 5', 'u.colon': '24 5', 'u.num': '13 5', 'u.numsemi': '13 5',
    'u.fmtonly': '2 5', 'u.fmtsemi': '24 5', 'u.lit': '2 5', 'u.litsemi': '5 5',
    'u.litval': '5 5', 'u.comma': '2 5', 'u.emptyonly': '2 5',
    'u.emptysemi': '5 5', 'u.strfield': '0 6', 'u.numnosemi': '2 5',
    'u.valcomma': '0 6', 'u.chan': '0 6', 'u.ok': '0 6', 'u.ok2': '0 6',
}

KNIVES = [
    dict(name="K-PU1",
         what="the missing-format test back to str_eval's tail -- re-merges the "
              "two meanings the slice split apart",
         old="                jp      z,loc_missing       ; `PRINT USING` -> ERR 24",
         new="                jp      z,pu_ifc            ; K-PU1",
         moves={'u.none': '5 5'}),
    dict(name="K-PU2",
         what="the not-a-string tail back to stmt_error -- the pre-slice ERR 2 "
              "for a numeric format",
         old="                jp      nc,type_mismatch_error  ; `PRINT USING 5` -> ERR 13 (0 B:",
         new="                jp      nc,stmt_error       ; K-PU2 (0 B:",
         moves={'u.num': '2 5', 'u.numsemi': '2 5'}),
    dict(name="K-PU3",
         what="accept ',' as the format separator again -- the row I had "
              "written down as a control and predicted wrong",
         # 🔴 THE FIRST DRAFT JUMPED TO A LABEL THAT DOES NOT EXIST. A knife
         # that cannot assemble is not a lenient knife, it is no knife -- the
         # cut has to introduce its own landing point.
         old=("                cp      ';'\n"
              "                jp      nz,stmt_error       ; ',' / EOL / a bare value -> ERR 2"),
         new=("                cp      ';'\n"
              "                jr      z,pu_k3_ok          ; K-PU3: accept ',' again\n"
              "                cp      ','\n"
              "                jp      nz,stmt_error\n"
              "pu_k3_ok:"),
         moves={'u.comma': '24 5'}),
    dict(name="K-PU4",
         what="the field-less raise back to a silent path -- re-creates the "
              "deleted pu_literal_only's ANSWER (not its printing)",
         old="                jp      nc,pu_ifc           ; no field -> ERR 5, values or not",
         new="                jp      nc,loc_missing      ; K-PU4",
         moves={'u.litsemi': '24 5', 'u.litval': '24 5', 'u.emptysemi': '24 5'}),
    dict(name="K-PU5",
         what="the ';'-with-no-values test removed -- restores the SILENT "
              "completion this slice's headline row reported",
         old="                jp      z,loc_missing       ; `PRINT USING\"##\";` -> ERR 24",
         new="                jp      z,pu_main           ; K-PU5",
         moves={'u.fmtsemi': '0 6'}),
]

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def build(tag):
    assert sh("rm -rf build", f"scratchpad/puknife_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/puknife_{tag}_build.log")


def zb_faces(tag):
    log = f"scratchpad/puknife_{tag}_probe.out"
    sh("python3 scratchpad/pusing_probe.py --sides=zb", log)
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
    assert not bad, f"baseline does not match pusing_after.out: {bad}"
    print(f"baseline {len(base_faces)} rows match pusing_after.out", flush=True)

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
