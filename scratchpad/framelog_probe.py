#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BRKLATCH: WHICH STOP latches does the interpreter consume, and when does it pause?
Logged EVERY FRAME on the VG-8020 and zerobas while a BASIC loop runs through a STOP press.

Our own code on the published H.TIMI hook ($FD9F): each interrupt appends INTFLG and the
loop's counter cell ($D0F2, bumped by the BASIC loop every iteration) to a buffer at $D100,
pointer at $D0F0, capped at $D4FF. The hook is installed address bytes FIRST, the `jp`
last, so an interrupt between the POKEs sees a `ret`. The harness reads the buffer from RAM
at the capture (mem_abs) -- the program never has to end. STOP held 0.2 / 0.5 / 1 / 2 s from
RUN+3.5 s. Black-box: work-area and our own RAM; no ROM byte.

    python3 -u scratchpad/framelog_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

# ROUND 2 (--key): the VG-8020's interpreter consumes INTFLG before the next H.TIMI
# (framelog_run.out: never non-zero there), so log the KEY instead -- NEWKEY row 7
# ($FBEC, STOP = bit 4, 0 = down) -- and capture the pointer, so only written frames count.
KEYLO, KEYHI = (0xEC, 0xFB) if "--key" in sys.argv else (0x9B, 0xFC)
# push af / push hl / ld hl,($D0F0) / ld a,h / cp $D5 / jr nc,out /
# ld a,(INTFLG) / ld (hl),a / inc hl / ld a,($D0F2) / ld (hl),a / inc hl / ld ($D0F0),hl /
# out: pop hl / pop af / ret
CODE = [0xF5, 0xE5, 0x2A, 0xF0, 0xD0, 0x7C, 0xFE, 0xD5, 0x30, 0x0D,
        0x3A, KEYLO, KEYHI, 0x77, 0x23, 0x3A, 0xF2, 0xD0, 0x77, 0x23, 0x22, 0xF0, 0xD0,
        0xE1, 0xF1, 0xC9]
assert CODE[10 + CODE[9]] == 0xE1   # jr nc lands on `pop hl` (0x0C missed it: caught here)
PROG = ["CLEAR 200,&HCFFF:FOR I=0 TO %d:READ X:POKE &HD000+I,X:NEXT" % (len(CODE) - 1),
        "POKE &HD0F0,0:POKE &HD0F1,&HD1:POKE &HD0F2,0",
        "POKE &HFDA0,0:POKE &HFDA1,&HD0:POKE &HFD9F,&HC3",
        "POKE &HD0F2,(PEEK(&HD0F2)+1) AND 255:GOTO 40",
        "DATA " + ",".join(str(b) for b in CODE)]
assert len(CODE) == 26
HOLDS = (0.7, 1.0, 2.0) if "--key" in sys.argv else (0.2, 0.5, 1.0, 2.0)   # --key: real presses 10 / 25 / 75 frames (hold - lead); 0.2 / 0.5 now RAISE


def summarize_key(hexs):
    b = bytes.fromhex(hexs)
    end = (b[0] | b[1] << 8) - 0xD100
    b = b[2:2 + max(0, end)]
    frames = [(b[i], b[i + 1]) for i in range(0, len(b) - 1, 2)]
    out, down, prev_c, stall0 = [], None, None, None
    for i, (k, c) in enumerate(frames):
        d = not (k & 0x10)
        if d != down:
            out.append(f"@{i}:{'DOWN' if d else 'up'}")
            down = d
        if prev_c is not None and c == prev_c:
            if stall0 is None:
                stall0 = i
        elif stall0 is not None:
            if i - stall0 >= 5:
                out.append(f"[stall @{stall0}..@{i}]")
            stall0 = None
        prev_c = c
    if stall0 is not None and len(frames) - stall0 >= 5:
        out.append(f"[stall @{stall0}..END]")
    return f"{len(frames)} frames: " + " ".join(out)


def summarize(hexs):
    b = bytes.fromhex(hexs)
    frames = [(b[i], b[i + 1]) for i in range(0, len(b) - 1, 2)]
    out, last_f, run_start, prev_c, stall = [], None, 0, None, 0
    for i, (f, c) in enumerate(frames):
        if f != last_f:
            out.append(f"@{i}:F{f}")
            last_f = f
        moving = prev_c is None or c != prev_c
        if not moving:
            stall += 1
        else:
            if stall >= 10:
                out.append(f"(stalled {stall}fr until @{i})")
            stall = 0
        prev_c = c
    if stall >= 10:
        out.append(f"(stalled {stall}fr to the end)")
    return f"{len(frames)} frames: " + " ".join(out)


def main():
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
        for h in HOLDS:
            raw = omsx_repl.run_cases(mach, [("stored", PROG)], batch=False,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                      holds=[((7, 0x10),)], hold_lead=0.5, hold_secs=h,
                                      capture=("mem_abs", [(0xD0F0, 2), (0xD100, 0x400)]))[0]
            fn = summarize_key if "--key" in sys.argv else (lambda r: summarize(r[4:]))
            print(f"{mach[:10]:10} hold {h:3.1f}  {fn(raw) if raw else '<NO CAPTURE>'}",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
