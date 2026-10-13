#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Do BASIC's persistent graphics cells and disk.rom's cells collide on the DISK build?

Reading sysvars.inc for RAM order step (2b): on the disk build the BASIC map's
GFX_DSCALE / GFX_DANGLE / GFX_G8N ($E95A..$E95D) sit on disk.rom's FAT_NUMFATS /
FAT_SECPERFAT / HOOK_SLOT (disk/equates.inc) -- a cross-ROM overlap the
D-BUFMERGE squeeze created ("in the gap before WBUF") and D-FATFLOOR preserved.
DRAW's S and A are PERSISTENT (spec G6 §4: only a power-on resets them).

  scale  DRAW"S8", a disk access (DSKF), then DRAW"BM10,20R10" -- S8 is 20 px
         (x 10..30), a scale overwritten with the FAT count 2 is 5 px.
  hook   VDP(7)=4 (writes G8N), then DSKF(0) -- does the disk still answer?

Prediction (2026-10-13): CF-3300 keeps S8 (POINT 25 and 29 lit) and answers;
zerobas loses the scale (POINT 25 unlit). The hook case: unknown.
"""
import os, sys
os.environ.setdefault("ZEROBAS_REFCACHE", "0")
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_R, "probes", "lib"), os.path.join(_R, "probes", "basic"),
                os.path.join(_R, "tools")]
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402
from make_test_dsk import Fat12Image               # noqa: E402
import basic_probe_graphics as g                   # noqa: E402

MACHINES = ("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK")
CASES = {
    "scale": (["SCREEN2:COLOR15,4:CLS:DRAW\"S8\":A=DSKF(0)",
               "DRAW\"BM10,20R10\":P=POINT(25,20):Q=POINT(29,20):R=POINT(31,20)",
               'SCREEN0:PRINT"S";P;Q;R'], "S"),
    "scale0": (["SCREEN2:COLOR15,4:CLS:DRAW\"S8\"",
                "DRAW\"BM10,20R10\":P=POINT(25,20):Q=POINT(29,20):R=POINT(31,20)",
                'SCREEN0:PRINT"S";P;Q;R'], "S"),
    "hook": (["VDP(7)=4:A=DSKF(0)", 'CLS:PRINT"H";A'], "H"),
}


def main():
    dsk = probe_tmp.tmp("diskalias.dsk")
    open(dsk, "wb").write(Fat12Image().finish())
    for name, (body, tag) in CASES.items():
        out = []
        for m in MACHINES:
            r = omsx_repl.run_cases(m, [("stored", body)], batch=False, reset=("", "SCREEN 0"),   # the CF-3300 boots in SCREEN 1: run 1 mangled its lines
                                    diska=dsk, run_gap=12.0)[0]
            out.append(g._answer(r, tag))
        print(f"{name:7s} CF-3300 {out[0]!r:16s} zerobas {out[1]!r:16s} "
              f"{'SAME' if out[0] == out[1] else 'DIFFERS'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
