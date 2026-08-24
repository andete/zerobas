#!/usr/bin/env python3
"""D-SWAP3 knives -- the deletion-based fix's three claims, each falsified.

The fix DELETES SWAP's bespoke third-operand rejection and lets exec_stmt's
generic statement-boundary guard reject the leftover `,C`/`,`. So SWAP now
exchanges A<->B and THEN raises ERR 2 at the boundary. Three independent value
cuts test the three load-bearing claims (the clean-HEAD before-run,
scratchpad/swap3_probe.out, is the natural revert: it reddens s.3cund/s.3all/
s.4all to `5 0` and s.ok3 to `5 1`).

  K-SW1  sw_absent jp gb_illegal -> jp stmt_error: every "B undefined -> ERR 5"
         row moves to ERR 2 and NOTHING else does. Direct proof that those ERR 5
         readings are the SECOND-operand rule -- which is why §4.5 recorded ERR 5
         for `SWAP A,B,C` (it ran with B undefined).
  K-SW2  the exchange's operand-1 write `ld (hl),a` -> `ld (hl),c` (A keeps its
         own byte): the value rows that read A after the swap move. Proves the
         exchange writes operand 1 BEFORE the boundary error.
  K-SW3  the exchange's operand-1 read `ld c,(hl)` -> `ld c,a` (B keeps its own
         byte): the value rows that read B move. Proves operand 2 is written too.

⚠️ SIGNATURE: `basic/*.asm` edit -> basic-reloc.rom + merged MOVE, sub.rom does NOT.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/missing.asm"

# the post-fix zb baseline (scratchpad/swap3_after2.out).
BASE = {
    's.3none': '5 0', 's.3bund': '5 0', 's.3cund': '2 0', 's.3all': '2 0',
    's.tc.def': '2 0', 's.tc.bun': '5 0', 's.tc.non': '5 0', 's.tc.va': '2 2',
    's.tc.vb': '2 1', 's.mm3': '13 0', 's.mm3v': '13 1', 's.4all': '2 0',
    's.2none': '5 0', 's.2bund': '5 0', 's.ok': '0 2', 's.ok3': '2 2',
    's.ok3b': '2 1', 'z.45.3': '5 0', 'z.45.tc': '5 0', 'z.45.one': '2 0',
    'z.45.lit': '2 0',
}

ABSENT = "                jp      gb_illegal          ; ERR 5 (Illegal function call)\n"
HLA = "                ld      (hl),a\n"
CHL = "                ld      c,(hl)\n"

KNIVES = [
    dict(name="K-SW1",
         what="sw_absent (2nd-operand rule) jp gb_illegal -> jp stmt_error (ERR 5->2)",
         old=ABSENT,
         new="                jp      stmt_error          ; K-SW1\n",
         moves={'s.3none': '2 0', 's.3bund': '2 0', 's.tc.bun': '2 0',
                's.tc.non': '2 0', 's.2none': '2 0', 's.2bund': '2 0',
                'z.45.3': '2 0', 'z.45.tc': '2 0'}),
    dict(name="K-SW2",
         what="exchange operand-1 write ld (hl),a -> ld (hl),c (A keeps its byte)",
         old=HLA,
         new="                ld      (hl),c              ; K-SW2\n",
         moves={'s.ok': '0 1', 's.ok3': '2 1', 's.tc.va': '2 1'}),
    dict(name="K-SW3",
         what="exchange operand-1 read ld c,(hl) -> ld c,a (B keeps its byte)",
         old=CHL,
         new="                ld      c,a                 ; K-SW3\n",
         moves={'s.ok3b': '2 2', 's.tc.vb': '2 2'}),
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
    assert sh("rm -rf build", f"scratchpad/swk_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/swk_{tag}_build.log")


def zb_faces(tag):
    log = f"scratchpad/swk_{tag}_probe.out"
    sh("python3 scratchpad/swap3_probe.py --sides=zb", log)
    faces = {}
    for line in open(log):
        if line.startswith("  ran zb "):
            parts = line.split(None, 3)
            faces[parts[2]] = parts[3].strip().strip("'")
    return faces


def main():
    original = open(SRC).read()
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
    print(f"baseline {len(base_faces)} rows match scratchpad/swap3_after2.out",
          flush=True)

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
    print(f"{exact}/{len(KNIVES)} knives EXACT")
    return 0 if exact == len(KNIVES) else 1


if __name__ == "__main__":
    sys.exit(main())
