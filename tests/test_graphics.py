# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: graphics G1 pixel-address math, sub/graphics.asm gfx_calc_addr
(the SCREEN-2 geometry engine's pure-leaf coordinate primitive).

docs/spec-basic-graphics-g1.md §6. Emulator-free (msxtest Z80 sim): assembles
the sub-ROM and drives gfx_calc_addr by label at rom_base=0 (the sub-ROM's own
page-0 org), same as tests/test_arrays.py drives the array engine.

Oracle: the SCREEN-2 VRAM landings PINNED black-box on the Philips VG-8020
(docs/spec-basic-graphics.md §11.2) -- pattern byte addr = (y>>3)*256 +
(x>>3)*8 + (y&7); bit mask = MSB-first $80 >> (x&7). Never ROM disassembly;
the address formula is the public TMS9918A GRAPHIC-2 layout, confirmed by the
black-box PSET landings (PSET(8,0)->VPEEK(8), PSET(0,8)->VPEEK(256),
PSET(255,191)->VPEEK(6143), PSET(3,0)-> bit $10).

gfx_calc_addr contract: in D=y (0..191), E=x (0..255); out HL=addr, C=mask.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = "/tmp/zb_graphics_sub.rom"
SYM = "/tmp/zb_graphics_sub.sym"

# (x, y) -> (expected pattern-byte address, expected MSB-first bit mask).
# The first five rows are the spec §6 table (the pinned landings); the rest add
# intra-byte bit coverage and a mid-screen point.
CASES = [
    # x,   y,    addr,  mask
    (0,   0,     0,    0x80),   # origin
    (8,   0,     8,    0x80),   # next char column -> +8 bytes (PSET(8,0)->VPEEK(8))
    (0,   8,   256,    0x80),   # next char row    -> +256 bytes (PSET(0,8)->VPEEK(256))
    (3,   0,     0,    0x10),   # x&7=3 -> $80>>3 (PSET(3,0)-> bit $10, same byte)
    (255, 191, 6143,   0x01),   # bottom-right pixel (PSET(255,191)->VPEEK(6143), bit $01)
    (1,   0,     0,    0x40),   # bit coverage within the origin byte
    (7,   0,     0,    0x01),   # last bit of the origin byte
    (9,   0,     8,    0x40),   # x=9 -> byte 8, bit x&7=1
    (128, 96, 3200,    0x80),   # a mid-screen point: (96>>3)*256 + (128>>3)*8 = 3072+128
    (255, 0,   248,    0x01),   # top row, last column byte
    (0,   191, 5895,   0x80),   # bottom-left: 23*256 + 7
]


def build():
    src = os.path.join(ROOT, "sub", "sub.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "sub"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True, cwd=ROOT)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=0)
    fails = 0
    for x, y, want_addr, want_mask in CASES:
        cpu = m.call("gfx_calc_addr", d=y, e=x)
        got_addr = cpu.hl
        got_mask = cpu.c
        ok = (got_addr == want_addr) and (got_mask == want_mask)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'} gfx_calc_addr x={x:>3} y={y:>3} -> "
              f"addr={got_addr:>5} (want {want_addr:>5})  "
              f"mask=${got_mask:02X} (want ${want_mask:02X})")
    print("-------------------")
    print("test_graphics:", "PASS" if fails == 0 else f"FAIL ({fails})")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
