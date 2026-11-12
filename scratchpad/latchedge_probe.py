#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The break-latch slice's first question: is INTFLG ($FC9B) latched on the press EDGE,
or every frame the key is held -- VG-8020 against zerobas? Our own code: ei, wait for
INTFLG != 0, value -> $D100, clear it, five frames with the key still held, INTFLG ->
$D101 (level: set again; edge: 0), then the key up (NEWKEY row 7 bit 4), one frame,
INTFLG -> $D102, cleared before returning (so BASIC's reaction is not in the reading).
Hold: stored program, lead 0.5 s, 2 s; CTRL-STOP and STOP. Black-box: work-area RAM.

    python3 -u scratchpad/latchedge_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CODE = [0xFB,                                     # 0  ei
        0x3A, 0x9B, 0xFC, 0xB7, 0x28, 0xFA,       # 1  w: ld a,(INTFLG) / or a / jr z,w
        0x32, 0x00, 0xD1,                         # 7  ld ($D100),a
        0xAF, 0x32, 0x9B, 0xFC,                   # 10 xor a / ld (INTFLG),a
        0x06, 0x05, 0x76, 0x10, 0xFD,             # 14 ld b,5 / halt / djnz
        0x3A, 0x9B, 0xFC, 0x32, 0x01, 0xD1,       # 19 ld a,(INTFLG) / ld ($D101),a
        0x76, 0x3A, 0xEC, 0xFB, 0xE6, 0x10, 0x28, 0xF8,   # 25 up: halt / NEWKEY+7 / and $10 / jr z,up
        0x76,                                     # 33 halt
        0x3A, 0x9B, 0xFC, 0x32, 0x02, 0xD1,       # 34 ld a,(INTFLG) / ld ($D102),a
        0xAF, 0x32, 0x9B, 0xFC, 0xC9]             # 40 xor a / ld (INTFLG),a / ret
assert CODE[5:7] == [0x28, 0xFA] and CODE[31:33] == [0x28, 0xF8]
PROG = ["CLEAR 200,&HCFFF:FOR I=0 TO %d:READ X:POKE &HD000+I,X:NEXT" % (len(CODE) - 1),
        'DEFUSR=&HD000:Q=USR(0):PRINT "[E";PEEK(&HD100);PEEK(&HD101);PEEK(&HD102);"]"',
        "DATA " + ",".join(str(b) for b in CODE)]
KEYS = {"ctrlstop": ((6, 0x02), (7, 0x10)), "stop": ((7, 0x10),)}


def main():
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
        names = list(KEYS)
        raws = omsx_repl.run_cases(mach, [("stored", PROG)] * len(names), batch=False,
                                   reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                   holds=[KEYS[n] for n in names], hold_lead=0.5, hold_secs=2.0)
        for n, scr in zip(names, raws):
            rows = [scr[i:i + 40].strip() for i in range(0, len(scr or ""), 40)]
            keep = [x for x in rows if x.startswith("[E") or "Break" in x or "rror" in x]
            print(f"{mach[:10]:10} {n:8} {' | '.join(keep) or '<NO OUTPUT>'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
