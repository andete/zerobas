#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCOVF -- simulate the three new routines' EXACT instruction sequences.

Cheaper than a build+boot round trip, and it catches the class of error that
D-LOCARG's first placement hit (an instruction sequence that is wrong on paper
before it is wrong in a ROM). Each function below is a line-for-line transcript
of the assembly in sub/graphics.asm -- registers as ints, flags explicit -- and
is checked against Python's own arithmetic over the FULL reachable domain edges
plus a wide random sweep.

    python3 -u scratchpad/circovf_asmsim.py
"""
from __future__ import annotations

import random
import sys

M16 = 0xFFFF


def sim_mul16r(de, a):
    """gfx_mul16r: HL := (DE*A + 128) >> 8, 24-bit accumulator C:HL."""
    hl = 0
    c = 0                       # ld hl,0 / ld c,l  -> C:HL = 0
    b = 8
    while True:
        cf = (hl >> 15) & 1     # add hl,hl
        hl = (hl << 1) & M16
        c = ((c << 1) | cf) & 0x1FF
        assert c <= 0xFF, "rl c carried out of the top byte"
        cf = (a >> 7) & 1       # add a,a
        a = (a << 1) & 0xFF
        if cf:                  # jr nc,gmr_skip
            t = hl + de         # add hl,de
            hl = t & M16
            if t > M16:         # jr nc / inc c
                c = (c + 1) & 0xFF
        b -= 1                  # djnz
        if not b:
            break
    t = hl + 128                # ld de,128 / add hl,de
    hl = t & M16
    if t > M16:
        c = (c + 1) & 0xFF
    return ((c << 8) | (hl >> 8)) & M16     # ld l,h / ld h,c


def sim_mul16u32(hl, de):
    """gfx_mul16u32: DE:HL := HL * DE  (DE = high word, HL = low word)."""
    bc = hl                     # ld b,h / ld c,l
    hl = 0
    a = 16
    while a:
        cf = (hl >> 15) & 1     # add hl,hl
        hl = (hl << 1) & M16
        e, d = de & 0xFF, de >> 8
        t = (e << 1) | cf       # rl e
        e, cf = t & 0xFF, t >> 8
        t = (d << 1) | cf       # rl d
        d, cf = t & 0xFF, t >> 8
        de = (d << 8) | e
        if cf:                  # jr nc,gm32_skip
            t = hl + bc         # add hl,bc
            hl = t & M16
            if t > M16:         # jr nc / inc de
                de = (de + 1) & M16
        a -= 1
    return de, hl               # high, low


def sim_cmp32(a_bytes, b_bytes):
    """gfx_cmp32: CF=1 iff a < b, 4-byte LE, borrow-propagating subtract."""
    cf = 0
    for i in range(4):
        t = a_bytes[i] - b_bytes[i] - cf
        cf = 1 if t < 0 else 0
    return cf


def le4(v):
    return [(v >> (8 * i)) & 0xFF for i in range(4)]


def main():
    rnd = random.Random(20260816)
    bad = 0

    # --- gfx_mul16r over its whole reachable domain edges + a random sweep ---
    cases = [(v, a) for v in (0, 1, 127, 128, 255, 256, 257, 32766, 32767)
             for a in (0, 1, 127, 128, 254, 255)]
    cases += [(rnd.randrange(0, 32768), rnd.randrange(0, 256))
              for _ in range(200000)]
    worst = 0
    for v, a in cases:
        got, want = sim_mul16r(v, a), (v * a + 128) >> 8
        worst = max(worst, want)
        if got != want:
            bad += 1
            print(f"  MUL16R MISS v={v} a={a}: got {got}, want {want}")
    print(f"  gfx_mul16r : {len(cases)} cases, max result {worst} "
          f"(${worst:04X}) -- $8000 {'REACHED' if worst >= 0x8000 else 'NOT reached'}")

    # the $8000 question, asked directly rather than argued
    m = max((sim_mul16r(32767, a) for a in range(256)))
    print(f"  gfx_mul16r : max over ASPS 0..255 at |v|=32767 is {m} (${m:04X});"
          f" the ASPS=256 arm returns |v| itself, max 32767 ($7FFF)")

    # --- gfx_mul16u32 ---
    cases = [(x, y) for x in (0, 1, 255, 256, 32767, 32639, 65535)
             for y in (0, 1, 255, 256, 32767, 32639, 65535)]
    cases += [(rnd.randrange(0, 65536), rnd.randrange(0, 65536))
              for _ in range(200000)]
    for x, y in cases:
        hi, lo = sim_mul16u32(x, y)
        got, want = (hi << 16) | lo, x * y
        if got != want:
            bad += 1
            print(f"  MUL16U32 MISS {x}*{y}: got {got}, want {want}")
    print(f"  gfx_mul16u32: {len(cases)} cases")

    # --- gfx_cmp32 ---
    vals = [0, 1, 255, 256, 65535, 65536, 0x7FFFFFFF, 0xFFFFFFFF,
            32767 * 32767, 32639 * 32639]
    cases = [(x, y) for x in vals for y in vals]
    cases += [(rnd.randrange(0, 1 << 32), rnd.randrange(0, 1 << 32))
              for _ in range(200000)]
    for x, y in cases:
        got, want = sim_cmp32(le4(x), le4(y)), int(x < y)
        if got != want:
            bad += 1
            print(f"  CMP32 MISS {x} vs {y}: got CF={got}, want {want}")
    print(f"  gfx_cmp32  : {len(cases)} cases")

    print()
    print(f"=== {'ALL THREE ROUTINES AGREE' if not bad else f'{bad} MISMATCHES'} ===")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
