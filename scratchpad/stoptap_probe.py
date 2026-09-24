#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-STOPTAP: how many times does ONE Ctrl-STOP press of a given length fire an
`ON STOP GOSUB` handler that only counts and RETURNs?

Filed 2026-09-25 from clrtrapstk_stop_probe.py's positive control (two 100 ms
taps: VG-8020 2, zerobas 11). D-STOPRELATCH measured the re-fire on LONG holds
(121 on the VG-8020) and made zerobas re-fire once per frame from the first
frame; a 5-frame tap firing ONCE on the reference says its re-fire waits first.
This sweeps the hold length and reads the count on both machines.

The driver is basic_probe_stop_trap.run(), imported not copied (it sits under
`make latch-check`). Clean room: the key matrix and RAM counters only.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import basic_probe_stop_trap as S                                 # noqa: E402

SIDES = [("vg8020", "Philips_VG_8020"),
         ("zb", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))]
FRAMES = (1, 3, 5, 10, 25, 50, 100)
FRAME = 0.02                                  # PAL
DOWN = 0.3

PROG = [
    S.CLR,
    "10 ON STOP GOSUB 100",
    "20 STOP ON",
    S.RANOK,
    "30 FORI=1TO10000:NEXT",                  # the tap lands in here
    "80 POKE&HD003,1:END",
    "100 POKE&HD000,PEEK(&HD000)+1",          # count, and ALWAYS return
    "108 RETURN",
]


def main() -> int:
    print(f"{'frames':>6} {'hold s':>6}  {'vg8020':>6} {'zb':>6}")
    for n in FRAMES:
        got = {}
        for side, mach in SIDES:
            r = S.run(mach, PROG, [(DOWN, DOWN + n * FRAME)])
            got[side] = (r or {}).get("flag") if r and r.get("done") else None
        v, z = got["vg8020"], got["zb"]
        mark = "" if v == z else "   DIFF"
        print(f"{n:6} {n*FRAME:6.2f}  {str(v):>6} {str(z):>6}{mark}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
