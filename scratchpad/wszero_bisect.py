#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO: bisect a diverging wszero-acceptance range on zerobas alone.

The VG-8020's answer is the same for every row (`[A][G] 1  2 XY]`, measured on
every run so far), so each step runs zerobas only: a synthetic tape (our own
cas_encode, the gate's own `tape()` shape: `ret` then $A5) over [lo, hi], the
gate's program, and the verdict OK / BAD against that answer. Halves until a
range of <= MIN bytes is bad, printing every step.

    python3 -u scratchpad/wszero_bisect.py LO HI [MIN] [--fill XX] [--noret]
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import omsx_repl                                    # noqa: E402
from cas_encode import build_cas                    # noqa: E402
import basic_probe_wszero as g                      # noqa: E402

GOOD = "[A][G] 1  2 XY]"
FILL = int(next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--fill"), "A5"), 16)
NORET = "--noret" in sys.argv


def bad(lo, hi):
    data = (bytes([FILL]) if NORET else bytes([0xC9])) + bytes([FILL]) * (hi - lo)
    path = os.path.join(tempfile.mkdtemp(prefix="wsbis_"), "t.cas")
    open(path, "wb").write(build_cas("W", lo, lo, data))
    prog = list(g.PROGRAM)
    if NORET:
        prog[1] = prog[1].replace(",R", "")
    got = g.rows(omsx_repl.run_cases("C-BIOS_MSX1_EU_REPACK_NODISK", [("direct", prog)],
                                     batch=False, reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                     run_gap=40.0, cassette=path)[0])
    v = got != GOOD
    print(f"  ${lo:04X}-${hi:04X} {'BAD' if v else 'ok '} [{got}]", flush=True)
    return v


def main():
    pos = [a for a in sys.argv[1:] if not a.startswith("--") and a != f"{FILL:02X}"]
    lo, hi = int(pos[0], 16), int(pos[1], 16)
    mn = int(pos[2]) if len(pos) > 2 else 4
    if not bad(lo, hi):
        print("the whole range is OK -- nothing to bisect")
        return 1
    while hi - lo + 1 > mn:
        mid = (lo + hi) // 2
        if bad(lo, mid):
            hi = mid
        elif bad(mid + 1, hi):
            lo = mid + 1
        else:
            print(f"NEITHER half alone is bad: an interaction across ${mid:04X}")
            return 3
    print(f"FATAL SPAN: ${lo:04X}-${hi:04X}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
