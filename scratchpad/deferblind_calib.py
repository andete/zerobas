#!/usr/bin/env python3
"""CALIBRATE deferblind_probe.py ON A KNOWN POSITIVE, before believing its zeros.

`scratchpad/deferblind_probe.py` reports that the FOR stack, the GOSUB stack and
the string heap all survive an IMMEDIATE trapped fault on all three machines --
27 of 27 readings agree. 🔴 **A SWEEP THAT FINDS ITS CLASS EMPTY IS A CLAIM
ABOUT THE INSTRUMENT FIRST.** Nine green rows say nothing until the row SHAPE
has been shown able to go red.

So: re-run the SAME probe, zb only, with K-FE1 applied -- `raise_error`'s
`ld (FN_FEND),a` turned into `ld (FN_TYP),a`, the one cut known to leave a
liveness cell standing. The calibration passes only if

    fn.imm   goes RED (5 -> the dead formal), and
    every other row stays exactly where it was.

If `fn.imm` also stayed green the probe would be measuring nothing, and the nine
zeros would be worthless. If OTHER rows moved, the cut is not as narrow as
claimed and the zeros would mean something different again.

The cut is IMPORTED from scratchpad/deffn_knives.py rather than retyped, so
there is one source of truth for what K-FE1 is.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scratchpad"))
import deffn_knives as K                                          # noqa: E402

PROBE = ["python3", "scratchpad/deferblind_probe.py", "--sides=zb"]
CUT = next(k for k in K.KNIVES if k[0].startswith("K-FE1"))
_, SRC, OLD, NEW, _, _, MOVES = CUT


def sh(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def build():
    sh(["rm", "-rf", "build"])
    r = sh(["make", "repack-machine"])
    if r.returncode:
        print((r.stdout + r.stderr)[-1500:])
    return r.returncode == 0


def rows(out):
    """label -> value, from the probe's own reporting lines."""
    d = {}
    for line in out.splitlines():
        if "zb='" in line and line.startswith("  ") and " ran " not in line:
            lab = line.split()[0]
            d[lab] = line.split("zb='", 1)[1].split("'", 1)[0]
    return d


def main() -> int:
    orig = SRC.read_text()
    assert orig.count(OLD) == 1, f"anchor matched {orig.count(OLD)}x"
    try:
        print("== clean build, baseline ==", flush=True)
        if not build():
            print("APPARATUS: clean build failed")
            return 3
        base_h = K.hashes()
        before = rows(sh(PROBE).stdout)
        print(f"baseline roms={dict(zip(K.RNAMES, base_h))}")
        print(f"baseline rows={before}", flush=True)
        if len(before) != 12:
            print(f"APPARATUS: {len(before)} rows parsed, expected 12")
            return 3

        SRC.write_text(orig.replace(OLD, NEW, 1))
        if not build():
            print("APPARATUS: knifed build failed")
            return 3
        h = K.hashes()
        mv = K.moved(base_h, h)
        if mv != MOVES:
            print(f"APPARATUS: wrong image moved: {sorted(mv)} != {sorted(MOVES)}")
            return 3
        after = rows(sh(PROBE).stdout)
        print(f"knifed  roms={dict(zip(K.RNAMES, h))}")
        print(f"knifed  rows={after}", flush=True)
    finally:
        SRC.write_text(orig)
        build()
        assert SRC.read_text() == orig, "source not restored!"
        print(f"restored roms={dict(zip(K.RNAMES, K.hashes()))}", flush=True)

    moved_rows = {l for l in before if before.get(l) != after.get(l)}
    print()
    for l in sorted(before):
        tag = "MOVED" if l in moved_rows else "same "
        print(f"  {tag}  {l:<8} {before[l]!r} -> {after.get(l)!r}")
    ok = moved_rows == {"fn.imm"}
    print(f"\nCALIBRATION: {'PASS' if ok else 'FAIL'} — moved={sorted(moved_rows)}, "
          f"want=['fn.imm']")
    if ok:
        print("The row shape CAN see a stale liveness cell. The nine zeros are "
              "a reading, not a silence.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
