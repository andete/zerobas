#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""fullclash-acceptance (D-FULLCLASH): a SCREEN 2 pixel that would make its
8-pixel byte full, in a colour other than the byte's foreground.

Found by the program ladder's L3_turtle: two squares in colours 2 and 3 meeting
at a corner read 2 there on the VG-8020 and 3 here. Measured
(scratchpad/drawclash_count.out, drawclash_vram.out): when setting the pixel
would make the pattern byte $FF and the colour differs from the byte's fg, the
VG-8020 CLEARS the pixel's bit and makes the colour the BACKGROUND, so the old
pixels keep their colour -- a full colour-2 byte plus `PSET(40,40),3` is
pattern $7F, colour $23; zerobas rewrote the fg and recoloured all eight. Same
colour, or one bit short of full: the ordinary clash. Seven rows, VPEEK of the
pattern and colour bytes and POINT of all eight pixels; both zerobas targets
against the VG-8020.

Clean-room: typed keys and a tape in; the printer port out (VPEEK / POINT
read the machine's own VRAM).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROG = "scratchpad/fullclash_probe.bas"
ROWS = 7


def main():
    text = open(os.path.join(REPO, PROG)).read()
    ref = run_programs.run(run_programs.REF, "fullclash", text)
    rl = ref[1].replace("\r", "").splitlines()
    print(f"{run_programs.REF:30} {ref[0]}  {len(rl)} rows")
    bad = 0
    for m in run_programs.ZB:
        zb = run_programs.run(m, "fullclash", text)
        zl = zb[1].replace("\r", "").splitlines()
        diff = [(a, b) for a, b in zip(rl, zl) if a != b]
        ok = len(rl) == ROWS and zl == rl
        bad += not ok
        print(f"{m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
        for a, b in diff:
            print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: a pixel that fills its byte keeps the "
          f"others' colour, as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
