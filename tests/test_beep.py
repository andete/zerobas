# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BASIC-ROM `ex_beep` (BEEP statement), no emulator.

BEEP is a repack-only feature (ROM_BASE < $4000), so this builds
basic/main-reloc.asm (ROM_BASE=$2812) and loads it at that base — the same as
test_sound.py / the string-engine tests.

This is the fast regression layer under the load-bearing VG-8020 PSG-trace
differential (probes/basic/basic_probe_beep.py). It locks the direct-PSG write
sequence — the tone-A period, the mixer read-modify-reconstruct, and the fixed
volume — by capturing every OUT the handler performs (msxtest record_out) and
feeding the R7 read-back via io_in.

Oracle basis (sound.asm §BEEP + the VG-8020 captures in spec-basic-audio-beep.md):
  BEEP has no arguments. It writes, in order:
    latch R7 (read-back; only the top two I/O-direction bits are reliable),
    R0=$55 R1=$00 (tone A period 85), R7=(curR7 & $C0)|$3E (mute B/C + noise, keep
    tone A + I/O bits), R8=$07 (fixed volume 7); then after a fixed delay
    R8=$00 (silence) and R7=(curR7 & $C0)|$38 (mixer wiped to the default, NOT the
    prior value). The restore is RECONSTRUCTED from the read-back I/O bits because
    R7's low 6 mixer bits do not read back (same limitation SOUND's R7 path has).
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = "/tmp/zb_beep.rom"
SYM = "/tmp/zb_beep.sym"
RELOC_BASE = 0x2812
BUF = 0xC000   # scratch token buffer (free RAM)


def build():
    src = os.path.join(ROOT, "basic", "main-reloc.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True, capture_output=True)


def run():
    build()
    fails = 0

    def report(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:44} -> {got!r}"
              + ("" if ok else f"   want {want!r}"))

    def beep_outs(cur_r7=0xB8):
        """Run ex_beep for `BEEP`; return the PSG-port ($A0/$A1) OUT log. io_in
        returns cur_r7 for the register-7 read-back."""
        m = Machine(ROM, SYM, rom_base=RELOC_BASE)
        BEEP_TOKEN = m.sym["BEEP_TOKEN"] if "BEEP_TOKEN" in m.sym else 0xC0
        m.poke(BUF, bytes([BEEP_TOKEN, 0x00]))     # no args; 0x00 line terminator
        m.cpu.io_in = lambda port: cur_r7          # only IN in the path is $A2 (R7 read)
        log = m.record_out()
        m.cpu.hl = BUF
        m.call("ex_beep")
        return [(p & 0xFF, v & 0xFF) for p, v in log if (p & 0xFF) in (0xA0, 0xA1)]

    def expect(cur_r7):
        io = cur_r7 & 0xC0
        return [
            (0xA0, 7),                    # latch R7 for the read-back
            (0xA0, 0), (0xA1, 0x55),      # R0 = tone A fine  (period low)
            (0xA0, 1), (0xA1, 0x00),      # R1 = tone A coarse (period high) -> $0055
            (0xA0, 7), (0xA1, io | 0x3E), # R7 = ioBits | $3E  (beep mixer, only tone A)
            (0xA0, 8), (0xA1, 0x07),      # R8 = fixed volume 7
            (0xA0, 8), (0xA1, 0x00),      # R8 = 0  (silence channel A)
            (0xA0, 7), (0xA1, io | 0x38), # R7 = ioBits | $38  (default mixer, wiped)
        ]

    # --- default idle mixer curR7=$b8 -> beep $be, restore $b8 -----------------
    report("BEEP curR7=b8 -> be then b8",  beep_outs(0xB8), expect(0xB8))
    # --- prior SOUND 7 set curR7=$be: restore still reconstructs to $b8 --------
    # (top bits 10 -> $80; be&C0==80, so identical write log to the b8 case; this
    #  is the host mirror of the differential's `sound 7,190:beep` case.)
    report("BEEP curR7=be -> be then b8",  beep_outs(0xBE), expect(0xBE))
    # --- a different I/O-bit pattern exercises the reconstruct path -------------
    report("BEEP curR7=40 -> 7e then 78",  beep_outs(0x40), expect(0x40))
    report("BEEP curR7=00 -> 3e then 38",  beep_outs(0x00), expect(0x00))
    report("BEEP curR7=c0 -> fe then f8",  beep_outs(0xC0), expect(0xC0))

    print("\n" + (f"{fails} FAILED" if fails else
                  "ALL PASS — ex_beep writes the PSG (tone 85, vol 7, mixer reconstruct) correctly"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
