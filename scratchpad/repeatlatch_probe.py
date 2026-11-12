#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BRKLATCH: does ZEROBAS's keyboard interrupt (C-BIOS) deliver auto-repeat STOP
latches during a long press, as the VG-8020's interpreter evidently receives one
(framelog_key.out: resumed ~36 frames into a 75-frame press)? Our own code on H.TIMI
logs INTFLG and NEWKEY row 7, then CLEARS INTFLG -- so each latch shows as its own
frame. zerobas only: on the VG-8020 the interpreter consumes the latch first. STOP held
for 75 frames (hold_lead 0.5, hold_secs 2.0 -- the release is counted from the RUN slot).

    python3 -u scratchpad/repeatlatch_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

# push af / push hl / ld hl,($D0F0) / ld a,h / cp $D5 / jr nc,out /
# ld a,(INTFLG) / ld (hl),a / inc hl / ld a,(NEWKEY+7) / ld (hl),a / inc hl /
# ld ($D0F0),hl / xor a / ld (INTFLG),a / out: pop hl / pop af / ret
CODE = [0xF5, 0xE5, 0x2A, 0xF0, 0xD0, 0x7C, 0xFE, 0xD5, 0x30, 0x11,
        0x3A, 0x9B, 0xFC, 0x77, 0x23, 0x3A, 0xEC, 0xFB, 0x77, 0x23, 0x22, 0xF0, 0xD0,
        0xAF, 0x32, 0x9B, 0xFC,
        0xE1, 0xF1, 0xC9]
assert CODE[10 + CODE[9]] == 0xE1      # jr nc lands on `pop hl`
PROG = ["CLEAR 200,&HCFFF:FOR I=0 TO %d:READ X:POKE &HD000+I,X:NEXT" % (len(CODE) - 1),
        "POKE &HD0F0,0:POKE &HD0F1,&HD1",
        "POKE &HFDA0,0:POKE &HFDA1,&HD0:POKE &HFD9F,&HC3",
        "GOTO 40",
        "DATA " + ",".join(str(b) for b in CODE)]


def main():
    raw = omsx_repl.run_cases("C-BIOS_MSX1_EU_REPACK_DISK", [("stored", PROG)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                              holds=[((7, 0x10),)], hold_lead=0.5, hold_secs=2.0,
                              capture=("mem_abs", [(0xD0F0, 2), (0xD100, 0x400)]))[0]
    b = bytes.fromhex(raw)
    end = (b[0] | b[1] << 8) - 0xD100
    b = b[2:2 + max(0, end)]
    ev, down = [], None
    for i in range(0, len(b) - 1, 2):
        f, k = b[i], b[i + 1]
        d = not (k & 0x10)
        if d != down:
            ev.append(f"@{i // 2}:{'DOWN' if d else 'up'}")
            down = d
        if f:
            ev.append(f"@{i // 2}:L{f}")
    print(f"zerobas {len(b) // 2} frames: " + " ".join(ev))
    return 0


if __name__ == "__main__":
    sys.exit(main())
