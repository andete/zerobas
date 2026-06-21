# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Unit test: BASIC-ROM `tokenise` (the crunch), no emulator.

A pure Tier-1 routine — HL = ASCII source, DE = token destination, no BIOS and
no I/O — so there is NOTHING to stub. We place an ASCII line in RAM, call
tokenise by symbol, and compare the emitted token bytes.

Expected bytes are built from the assembler's OWN named token constants (pasmo
emits the equs into the symbol file), so the test can never silently drift from
sysvars.inc. The crunch the real ROM produces is already oracle-validated
byte-for-byte against a Philips VG-8020 by basic_probe_crunch.py; this locks that
behaviour in as a fast, emulator-free regression. It also exercises the core on
a rich opcode set: match_kw's IX/IY table walk, the *10 digit loop, branch_lineno.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = "/tmp/zerobas_basic_ut.rom"
SYM = "/tmp/zerobas_basic_ut.sym"
SRC = 0xC000          # ASCII source line (free RAM)
DST = 0xC100          # token output buffer


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def crunch(m, text, n):
    # Compare a FIXED count of bytes, not "up to the first 0x00": a token stream
    # can legitimately contain 0x00 operand bytes (e.g. the high byte of a small
    # line number in $0E,<lo>,<hi>), so scanning for a terminator would truncate.
    m.poke(SRC, text.encode("ascii") + b"\x00")
    m.mem[DST:DST + 64] = b"\x00" * 64
    m.call("tokenise", hl=SRC, de=DST)
    return list(m.mem[DST:DST + n])


def run():
    build()
    m = Machine(ROM, SYM)
    s = m.sym
    DIGIT = s["INT_DIGIT_BASE"]
    SP = 0x20

    cases = [
        # text          expected token stream (incl. trailing 0 terminator)
        ("?5",          [s["PRINT_TOKEN"], DIGIT + 5, 0]),
        ("PRINT 5",     [s["PRINT_TOKEN"], SP, DIGIT + 5, 0]),
        ("A=1",         [ord("A"), s["EQ_TOKEN"], DIGIT + 1, 0]),
        # GOTO <n>: branch_lineno emits the line-number ref $0E,<lo>,<hi>
        ("GOTO 10",     [s["GOTO_TOKEN"], SP, s["LINENO_TOKEN"], 10, 0, 0]),
    ]

    fails = 0
    for text, want in cases:
        got = crunch(m, text, len(want))
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {text!r:12} -> "
              f"{' '.join(f'{b:02x}' for b in got)}"
              + ("" if ok else f"   want {' '.join(f'{b:02x}' for b in want)}"))

    print()
    print("ALL PASS — crunch matches the oracle-validated token format"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
