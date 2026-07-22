#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G4 arc-vector bug bisection (post ellipse-fix, coordinator-directed).

Runs CIRCLE(60,60),15,15,0,1.57 on zerobas and reads back the RESIDENT-
computed GFX_SVX/GFX_SVY/GFX_EVX/GFX_EVY (basic/sysvars.inc: $E130/$E132/
$E134/$E136) directly from RAM via openMSX debug read, no BASIC PEEK/PRINT
in between (avoids any "subsequent statement contaminates scratch" risk).

Expected (host-fit oracle, scratchpad/g4_circle_fit.py rscale_vec_nudge):
  S = (15, 0)   (a0=0: cos=1,sin=0 exactly)
  E = (1, -15)  (a1=1.57: cos(1.57)=+0.0008 nudges to +1; sin(1.57)~15 -> -15)
"""
from __future__ import annotations
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

GFX_CXC, GFX_CYC, GFX_R = 0xE126, 0xE128, 0xE12A
GFX_ASPMAJ, GFX_ASPS, GFX_ARCF = 0xE12C, 0xE12D, 0xE12F
GFX_SVX, GFX_SVY, GFX_EVX, GFX_EVY = 0xE130, 0xE132, 0xE134, 0xE136
GFX_ARCBIG = 0xE138
GFX_ATMP = 0xE14C


def s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def dump(label, ops, want_s, want_e):
    body = [f"SCREEN2:{ops}", "GOTO 20"]
    segs = [(GFX_CXC, 2), (GFX_CYC, 2), (GFX_R, 2), (GFX_ASPMAJ, 1), (GFX_ASPS, 2),
            (GFX_ARCF, 1), (GFX_SVX, 2), (GFX_SVY, 2), (GFX_EVX, 2), (GFX_EVY, 2),
            (GFX_ARCBIG, 1)]
    out = omsx_repl.run_cases(ZB, [("stored", body)], batch=False, capture=("mem_abs", segs))[0]
    b = bytes.fromhex(out)
    cxc, cyc, r = struct.unpack("<hhh", b[0:6])
    aspmaj = b[6]
    asps = struct.unpack("<H", b[7:9])[0]
    arcf = b[9]
    svx, svy, evx, evy = struct.unpack("<hhhh", b[10:18])
    arcbig = b[18]
    print(f"  {label:12s} {ops}")
    print(f"    centre=({cxc},{cyc}) r={r} aspmaj={aspmaj} asps={asps} arcf={arcf} arcbig={arcbig}")
    print(f"    S=({svx},{svy})  want {want_s}   {'OK' if (svx,svy)==want_s else '**MISMATCH**'}")
    print(f"    E=({evx},{evy})  want {want_e}   {'OK' if (evx,evy)==want_e else '**MISMATCH**'}")
    return (svx, svy), (evx, evy)


def main():
    print("=== G4 arc-vector bisection: resident GFX_SVX/SVY/EVX/EVY ===")
    dump("arc_0_hpi", "CIRCLE(60,60),15,15,0,1.57", (15, 0), (1, -15))
    dump("arc_hpi_pi", "CIRCLE(60,60),15,15,1.57,3.14", (1, -15), (-15, -1))
    dump("arc_wrap", "CIRCLE(60,60),15,15,3,1", (-15, -2), (8, -13))
    dump("spoke_270", "CIRCLE(60,60),15,15,-1.57,0", (1, -15), (15, 0))


if __name__ == "__main__":
    main()
