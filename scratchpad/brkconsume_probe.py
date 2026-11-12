#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""After machine code has taken a CTRL-STOP through BREAKX, the VG-8020's BASIC does not
also break and zerobas's does (outdlp_fail_fixed.out, breakx_loop). What happens to
INTFLG ($FC9B)? Our own code: lp: call BREAKX / jr nc,lp -- then INTFLG -> $D100 at
once, -> $D101 five frames later (the key still held), then wait for the key up
(NEWKEY row 7 bit 4), five frames, INTFLG -> $D102 -- NOTHING cleared, so BASIC's own
reaction afterwards is part of the reading. Hold: stored program, lead 0.5 s, 2 s (the
hold outdlp_fail_probe.py proved). Black-box: work-area RAM and the screen.

    python3 -u scratchpad/brkconsume_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CODE = [0xFB,                                     # ei
        0xCD, 0xB7, 0x00, 0x30, 0xFB,             # lp: call BREAKX / jr nc,lp
        0x3A, 0x9B, 0xFC, 0x32, 0x00, 0xD1,       # ld a,(INTFLG) / ld ($D100),a
        0x06, 0x05, 0x76, 0x10, 0xFD,             # ld b,5 / halt / djnz
        0x3A, 0x9B, 0xFC, 0x32, 0x01, 0xD1,       # ld a,(INTFLG) / ld ($D101),a
        0x76, 0x3A, 0xEC, 0xFB, 0xE6, 0x10, 0x28, 0xF8,   # up: halt / ld a,(NEWKEY+7) / and $10 / jr z,up
        0x06, 0x05, 0x76, 0x10, 0xFD,             # ld b,5 / halt / djnz
        0x3A, 0x9B, 0xFC, 0x32, 0x02, 0xD1,       # ld a,(INTFLG) / ld ($D102),a
        0xC9]
PROG = ["CLEAR 200,&HCFFF:FOR I=0 TO %d:READ X:POKE &HD000+I,X:NEXT" % (len(CODE) - 1),
        'DEFUSR=&HD000:Q=USR(0):PRINT "[I";PEEK(&HD100);PEEK(&HD101);PEEK(&HD102);PEEK(&HFC9B);"]"',
        'PRINT "[C END]"',
        "DATA " + ",".join(str(b) for b in CODE)]
CTRL_STOP = ((6, 0x02), (7, 0x10))


def main():
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
        scr = omsx_repl.run_cases(mach, [("stored", PROG)], batch=False,
                                  reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                  holds=[CTRL_STOP], hold_lead=0.5, hold_secs=2.0)[0]
        rows = [scr[i:i + 40].strip() for i in range(0, len(scr or ""), 40)]
        keep = [x for x in rows if x.startswith("[I") or x.startswith("[C") or "Break" in x
                or "rror" in x]
        print(f"{mach[:10]:10} {' | '.join(keep) or '<NO OUTPUT>'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
