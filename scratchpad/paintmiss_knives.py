#!/usr/bin/env python3
"""D-PAINTMISS knives -- six size-neutral cuts, each with a predicted row set.

Every knife obeys the tree's rules: it cuts a VALUE (never a call, and never a
jump whose removal orphans a label -- `make deadcode` would then build no ROM
at all), it is preceded by `rm -rf build`, it RESTORES BY WRITING THE BYTES
(never shutil.copy2), and it asserts WHICH image moved.

⚠️ THE SIGNATURE HERE IS THE OPPOSITE OF D-CIRCMISS'S. This is a `basic/*.asm`
edit: `basic-reloc.rom` AND the merged `zerobas-main-eu.rom` must move, and
`sub.rom` must NOT.

THE POINT OF THE SLICE IS K-PM1 / K-PM2 / K-PM5, not K-PM3 / K-PM4 / K-PM6.
`ep_default_b` is a SHARED TAIL and two of its six jumps are the LEGITIMATE
omissions; the differential's four green trap rows are only detectors if a
knife can redden them one at a time. [[a-shared-tail-is-not-a-decision]]
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/graphics.asm"

# the post-fix zerobas baseline (scratchpad/paintmiss_after.out), PAINT rows only
BASE = {
    'p.colour': '24 4', 'p.kcolour': '24 4',
    'p.b': '24 4', 'p.kb': '24 4', 'p.cc': '24 4', 'p.kcc': '24 4',
    'p.none': '0 15', 'p.omit': '0 15', 'p.plain': '0 15', 'p.ok': '0 15',
}

NOFIELDS = "                jr      nz,ep_default_b     ; no fields at all -> C=FORCLR, B=C\n"
NOB      = '                jr      nz,ep_default_b     ; no ",B" -> B = C\n'
CSLOT    = ("                or      a\n"
            "                jr      z,ep_missing        ; dangling comma -> ERR 24\n"
            "                cp      COLON\n"
            "                jr      z,ep_missing\n"
            "                ; --- given C:")
BSLOT    = ("                or      a\n"
            "                jr      z,ep_missing        ; dangling comma -> ERR 24\n"
            "                cp      COLON\n"
            "                jr      z,ep_missing\n"
            "                cp      ','\n")
CEMPTY   = "ep_c_empty:\n                inc     hl                  ; consume the shared comma\n"
RAISER   = "ep_missing:\n                jp      loc_missing         ; ERR 24 (Missing operand)\n"

KNIVES = [
    dict(name="K-PM1",
         what="the `no fields at all` exit (`PAINT(x,y)`) -> ep_missing: one "
              "LEGITIMATE omission pointed at the new raiser",
         old=NOFIELDS,
         new="                jr      nz,ep_missing       ; K-PM1\n",
         moves={'p.none': '24 4'}),
    dict(name="K-PM2",
         what="the `no ,B` exit (`PAINT(x,y),15`) -> ep_missing: the OTHER "
              "legitimate omission pointed at the new raiser",
         old=NOB,
         new="                jr      nz,ep_missing       ; K-PM2\n",
         moves={'p.plain': '24 4'}),
    dict(name="K-PM3",
         what="the C slot's end-of-statement arm reverted to ep_default_b -- "
              "the defect, re-created at ONE of its four sites",
         old=CSLOT,
         new=("                or      a\n"
              "                jr      z,ep_default_b      ; K-PM3\n"
              "                cp      COLON\n"
              "                jr      z,ep_missing\n"
              "                ; --- given C:"),
         moves={'p.colour': '0 15'}),
    dict(name="K-PM4",
         what="the B slot's end-of-statement arm reverted to ep_default_b -- "
              "ONE instruction, and TWO rows must move, by two different routes",
         old=BSLOT,
         new=("                or      a\n"
              "                jr      z,ep_default_b      ; K-PM4\n"
              "                cp      COLON\n"
              "                jr      z,ep_missing\n"
              "                cp      ','\n"),
         moves={'p.b': '0 15', 'p.cc': '0 15'}),
    dict(name="K-PM5",
         what="ep_c_empty's `inc hl` -> `nop`: the shared comma is no longer "
              "consumed, so ep_parse_b sees it as a 4th argument (ERR 2). This "
              "is the ONLY knife that reddens p.omit, the legal C-omitted-"
              "BETWEEN-commas form that no other row pins",
         old=CEMPTY,
         new="ep_c_empty:\n                nop                         ; K-PM5\n",
         moves={'p.cc': '2 4', 'p.kcc': '2 4', 'p.omit': '2 4'}),
    dict(name="K-PM6",
         what="ep_missing `jp loc_missing` -> `jp gfx_err5`: WRONG CODE, and "
              "the prediction is that the PICTURE is still protected (R stays 4)",
         old=RAISER,
         new="ep_missing:\n                jp      gfx_err5            ; K-PM6\n",
         moves={k: '5 4' for k in ('p.colour', 'p.kcolour', 'p.b', 'p.kb',
                                   'p.cc', 'p.kcc')}),
]

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def build(tag):
    assert sh("rm -rf build", f"scratchpad/pmknife_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/pmknife_{tag}_build.log")


def zb_faces(tag):
    log = f"scratchpad/pmknife_{tag}_probe.out"
    rc = sh("python3 scratchpad/circmiss_sib2.py --sides=zb p.", log)
    faces = {}
    for line in open(log):
        if line.startswith("  ran zb "):
            parts = line.split(None, 3)
            faces[parts[2]] = parts[3].strip().strip("'")
    return rc, faces


def main():
    original = open(SRC).read()
    for k in KNIVES:
        assert original.count(k["old"]) == 1, f"{k['name']}: anchor not unique"

    print("=== baseline ===", flush=True)
    assert build("base") == 0, "baseline build failed"
    base_h = hashes()
    print("baseline roms=" + " / ".join(base_h), flush=True)
    rc, base_faces = zb_faces("base")
    assert set(base_faces) == set(BASE), f"baseline row set {sorted(base_faces)}"
    for row, want in BASE.items():
        assert base_faces[row] == want, \
            f"baseline row {row}: {base_faces[row]!r} != documented {want!r}"
    print(f"baseline {len(base_faces)} rows match scratchpad/paintmiss_after.out",
          flush=True)

    exact = 0
    for k in KNIVES:
        name = k["name"]
        open(SRC, "w").write(original.replace(k["old"], k["new"]))
        assert build(name) == 0, f"{name}: build failed -- see the log"
        h = hashes()
        # a basic/*.asm cut moves basic-reloc.rom AND the merged image, NOT sub.rom
        assert h[0] != base_h[0], f"{name}: basic-reloc.rom did NOT move -- the cut did not land"
        assert h[2] != base_h[2], f"{name}: merged image did NOT move"
        assert h[1] == base_h[1], f"{name}: sub.rom moved -- wrong image"
        print(f"\n{name}  roms={' / '.join(h)}", flush=True)
        print(f"  cut: {k['what']}", flush=True)
        rc, faces = zb_faces(name)
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
            print(f"  EXACT -- {len(k['moves'])} predicted, {len(moved)} moved",
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
