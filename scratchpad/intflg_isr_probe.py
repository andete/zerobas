#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3a), ISCNTC's input: does the keyboard interrupt set INTFLG ($FC9B) when
STOP or CTRL-STOP is held -- VG-8020 against zerobas?

ISCNTC / CKCNTC act on INTFLG (iscntc_run3.out: 3 -> Break, 4 -> wait). That only means
something if the ISR SETS it. Our own machine code, so the interpreter is not running:
`ei`, then 250 frames of `halt` / `ld a,($FC9B)` / `ld (hl),a` into $D200.., then
INTFLG := 0 (or the VG-8020's interpreter breaks between statements on the way out). The
key is HELD from about RUN + 1.5 s for 2 s. BASIC then prints how many frames read each
value and the first frame that read non-zero. Black-box: work-area RAM only.

    python3 -u scratchpad/intflg_isr_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

N = 100   # 2 s: ends while the key is down (hold ~RUN+1.5..3.5), then waits for the release
# 🔴 CONTROL (2026-11-12): the first run read INTFLG 0 on EVERY frame on BOTH machines,
# CTRL-STOP held included -- which an unlanded hold reads too. So each frame also counts
# NEWKEY row 7 ($FBEC, STOP = bit 4, 0 = down): K. It read K = 0 twice -- run_cases moves
# a hold to RUN + run_gap + hold_lead, AFTER this loop. Now: no run_gap, the counting in
# the machine code, and it returns only once STOP is up again (no BASIC loop to outlast).
#   ei / ld hl,0 / ld c,0 / ld b,250
#   loop: halt / ld a,(INTFLG) / or a / jr z,s1 / inc l / ld e,a / ld a,c / or a /
#         jr nz,s1 / ld c,e
#   s1:   ld a,(NEWKEY+7) / and $10 / jr nz,s2 / inc h
#   s2:   djnz loop
#   wait: halt / ld a,(NEWKEY+7) / and $10 / jr z,wait
#   xor a / ld (INTFLG),a / ld ($D100),hl / ld a,c / ld ($D102),a / ret
CODE = [0xFB, 0x21, 0x00, 0x00, 0x0E, 0x00, 0x06, N,
        0x76, 0x3A, 0x9B, 0xFC, 0xB7, 0x28, 0x07, 0x2C, 0x5F, 0x79, 0xB7, 0x20, 0x01, 0x4B,
        0x3A, 0xEC, 0xFB, 0xE6, 0x10, 0x20, 0x01, 0x24,
        0x10, 0xE8,
        0x76, 0x3A, 0xEC, 0xFB, 0xE6, 0x10, 0x28, 0xF8,
        # (released) LATCH OR LEVEL? 10 frames after the release, INTFLG -> $D103:
        # ld b,10 / halt / djnz -1 / ld a,(INTFLG) / ld ($D103),a
        0x06, 0x0A, 0x76, 0x10, 0xFD, 0x3A, 0x9B, 0xFC, 0x32, 0x03, 0xD1,
        0xAF, 0x32, 0x9B, 0xFC, 0x22, 0x00, 0xD1, 0x79, 0x32, 0x02, 0xD1, 0xC9]
assert CODE[30:32] == [0x10, 0xE8] and len(CODE) == 63
PROG = [
    "CLEAR 200,&HCFFF",
    f"FOR I=0 TO {len(CODE) - 1}:READ X:POKE &HD000+I,X:NEXT",
    "DEFUSR=&HD000:Q=USR(0)",
    'PRINT "[H";PEEK(&HD100);"K";PEEK(&HD101);"V";PEEK(&HD102);"R";PEEK(&HD103);"]"',
    "DATA " + ",".join(str(b) for b in CODE),
]
CASES = {"stop": ((7, 0x10),), "ctrlstop": ((6, 0x02), (7, 0x10))}


def main():
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
        names = list(CASES)
        raws = omsx_repl.run_cases(mach, [("stored", PROG)] * len(names), batch=False,
                                   holds=[CASES[n] for n in names], hold_lead=0.5,
                                   hold_secs=2.0, step=1.0)
        for n, raw in zip(names, raws):
            txt = " ".join("".join(raw or "").split())
            i = txt.rfind("[H ")           # the PRINTED row, not the listing's echo
            print(f"{mach:28} {n:9} {txt[i:i + 60] if i >= 0 else '<NO [H] ROW> ' + txt[-120:]!r}",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
