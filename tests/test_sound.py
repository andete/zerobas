# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BASIC-ROM `ex_sound` (SOUND statement), no emulator.

SOUND is a repack-only feature (ROM_BASE < $4000), so this builds
basic/main-reloc.asm (ROM_BASE=$2812) and loads it at that base — the same as
test_input.py / the string-engine tests.

This is the fast regression layer under the load-bearing VG-8020 differential
(probes/basic/basic_probe_sound.py). It locks the PSG-write logic — the direct
OUT latch/data sequence and the register-7 read-modify-write mask — by capturing
every OUT the handler performs (msxtest record_out) and feeding the R7 read-back
via io_in. The error surface (register 0..13, byte coercion → ERR 5/6) is proven
end-to-end by the differential, not re-derived here.

Oracle basis (sound.asm + the VG-8020 captures in its header):
  * registers 0..6, 8..13: latch the register number on $A0, write the whole
    value byte on $A1.
  * register 7 (mixer): read the current R7 (latch 7 on $A0, read $A2), keep its
    top two I/O-direction bits, take bits 0..5 from the value:
    R7' = (curR7 & $C0) | (value & $3F).

Token encoding (sysvars.inc): SOUND_TOKEN then eval-decodable operand tokens —
digit 0..9 -> $11+n; 10..255 -> $0F <byte>; ',' -> $2C; 0x00 line terminator.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = "/tmp/zb_sound.rom"
SYM = "/tmp/zb_sound.sym"
RELOC_BASE = 0x2812
BUF = 0xC000   # scratch token buffer (free RAM)


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True, capture_output=True)


def enc(v):
    """eval-decodable token bytes for a small non-negative integer literal."""
    if v <= 9:
        return bytes([0x11 + v])          # single-digit token $11+n
    assert v <= 255
    return bytes([0x0F, v])               # one-byte int token $0F <byte>


def run():
    build()
    fails = 0

    def report(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:44} -> {got!r}"
              + ("" if ok else f"   want {want!r}"))

    def sound_outs(reg, val, cur_r7=0xB8):
        """Run ex_sound for `SOUND reg,val`; return the (port,val) OUT log. io_in
        returns cur_r7 for the register-7 read-back."""
        m = Machine(ROM, SYM, rom_base=RELOC_BASE)
        SOUND_TOKEN = m.sym["SOUND_TOKEN"] if "SOUND_TOKEN" in m.sym else 0xC4
        m.poke(BUF, bytes([SOUND_TOKEN]) + enc(reg) + b"," + enc(val) + b"\x00")
        m.poke(m.sym["FPERR"], b"\x00")       # exec_stmt clears it per statement; we call direct
        m.cpu.io_in = lambda port: cur_r7     # only IN in the path is $A2 (R7 read)
        log = m.record_out()
        m.cpu.hl = BUF
        m.call("ex_sound")
        # keep only the PSG ports ($A0 latch / $A1 data); ignore any incidental I/O
        return [(p & 0xFF, v & 0xFF) for p, v in log if (p & 0xFF) in (0xA0, 0xA1)]

    # --- registers 0..6, 8..13: full value byte, latch-then-data ---------------
    report("SOUND 0,255  -> latch 0, data ff",   sound_outs(0, 255),  [(0xA0, 0), (0xA1, 0xFF)])
    report("SOUND 1,42   -> latch 1, data 2a",   sound_outs(1, 42),   [(0xA0, 1), (0xA1, 0x2A)])
    report("SOUND 6,31   -> latch 6, data 1f",   sound_outs(6, 31),   [(0xA0, 6), (0xA1, 0x1F)])
    report("SOUND 8,255  -> latch 8, data ff",   sound_outs(8, 255),  [(0xA0, 8), (0xA1, 0xFF)])
    report("SOUND 13,255 -> latch 13, data ff",  sound_outs(13, 255), [(0xA0, 13), (0xA1, 0xFF)])
    report("SOUND 0,0    -> latch 0, data 00",   sound_outs(0, 0),    [(0xA0, 0), (0xA1, 0x00)])

    # --- register 7 (mixer): R7' = (curR7 & $C0) | (val & $3F) -----------------
    # The write sequence latches 7 (read-back), then latches 7 again + writes data.
    # curR7=$B8 (10111000): top 2 bits = 10 -> $80 preserved.
    report("SOUND 7,255 curR7=b8 -> data bf",
           sound_outs(7, 255, 0xB8), [(0xA0, 7), (0xA0, 7), (0xA1, 0xBF)])   # $80|$3F
    report("SOUND 7,192 curR7=b8 -> data 80",
           sound_outs(7, 192, 0xB8), [(0xA0, 7), (0xA0, 7), (0xA1, 0x80)])   # $80|$00
    report("SOUND 7,63  curR7=b8 -> data bf",
           sound_outs(7, 63, 0xB8),  [(0xA0, 7), (0xA0, 7), (0xA1, 0xBF)])   # $80|$3F
    # a different current R7 exercises the preserve path (top bits 01 -> $40).
    report("SOUND 7,0   curR7=40 -> data 40",
           sound_outs(7, 0, 0x40),   [(0xA0, 7), (0xA0, 7), (0xA1, 0x40)])   # $40|$00

    print("\n" + (f"{fails} FAILED" if fails else
                  "ALL PASS — ex_sound writes the PSG (mask R7 top 2 bits) correctly"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
