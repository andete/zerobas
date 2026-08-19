# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BASIC-ROM `print_number` and `print_crlf` (print.asm), no emulator.

Tier-2 (BIOS-stub) tests: CHPUT is trapped and every emitted byte accumulated.

Entry conventions (derived from print.asm and its call sites):
  - print_number: DE = signed-16 value (see print.asm:187-49 — `call eval` puts
    the result in DE, then `call print_number`; also list.asm:198 loads DE from
    the line-number BC pair before calling list_num which mirrors the same path).
  - print_crlf:   no argument; emits CR ($0D) then LF ($0A) via CHPUT.

Number format (from the print.asm module comment and the code at pn_neg/pn_conv/
pn_tail):
  - Non-negative: leading space (sign placeholder, NUMBUF[0] = ' ') + decimal
    digits, no leading zeros + trailing space (pn_tail writes ' ' then 0).
  - Negative: leading '-' (NUMBUF[0] = '-') + decimal magnitude + trailing space.
  - The decimal digits are the standard base-10 representation (independently
    derivable: just Python's str(abs(value))).
  This matches the documented MSX-BASIC PRINT-integer contract (public language
  reference: "a leading space for non-negative values, '-' for negative, the
  decimal digits with no leading zeros, and a trailing space").

Oracle basis:
  - Digit values: base-10 arithmetic (pure math, no reference ROM).
  - Framing (leading space/'-', trailing space): cited from print.asm module
    comment + code (pn_neg stores '-', non-negative stores ' '; pn_tail appends
    ' ' before the 0-terminator).
  - CR/LF values: control-character definitions (CR = 13 = 0x0D, LF = 10 = 0x0A;
    standard ASCII; also asserted from print.asm:411-165 which loads literal 13
    and 10).
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

# The image under test is loaded at its ORG. Named here rather than
# defaulted: msxtest.Machine's old default was $4000, the retired lean
# cart's org, so a BASIC test that omitted it silently tested the lean
# build (docs/spec-lean-retire-s3-gates.md §5, F-U).
BASIC_BASE = 0x2812

ROM = "/tmp/zb_print.rom"
SYM = "/tmp/zb_print.sym"


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def expected_number(value):
    """Build the expected byte sequence for print_number(DE=value).

    Oracle: print.asm module comment + code pn_neg/pn_conv/pn_tail.
      - Non-negative: b' ' + decimal digits + b' '
      - Negative:     b'-' + decimal magnitude + b' '
    The decimal digits are independently derivable from base-10 arithmetic
    (Python's str() of the absolute value).
    """
    if value < 0:
        sign = b'-'
        mag = -value
    else:
        sign = b' '
        mag = value
    digits = str(mag).encode('ascii')
    return sign + digits + b' '


def run():
    build()
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)

    fails = 0

    # -----------------------------------------------------------------------
    # print_crlf: must emit exactly CR ($0D) then LF ($0A).
    # Oracle: ASCII control codes CR=13/LF=10; confirmed by print.asm:411-165
    # which loads literal 13 then 10.
    # -----------------------------------------------------------------------
    out = m.capture_chput()
    m.call("print_crlf")
    got = bytes(out)
    want = bytes([0x0D, 0x0A])
    ok = got == want
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  print_crlf  -> "
          f"{got!r}" + ("" if ok else f"   want {want!r}"))

    # -----------------------------------------------------------------------
    # print_number: DE = signed-16 value -> CHPUT stream.
    # Oracle: expected_number() computes the framing from the print.asm docs
    # and the pn_neg/pn_conv/pn_tail code.
    #
    # Cases:
    #   0       -> ' 0 '     (non-negative, single zero digit, sign space + trailing space)
    #   42      -> ' 42 '    (non-negative, two digits)
    #   -7      -> '-7 '     (negative, single digit)
    #   12345   -> ' 12345 ' (non-negative, five digits — exercises the full div10 loop)
    #   32767   -> ' 32767 ' (max signed 16-bit positive)
    #   -32768  -> '-32768 ' (min signed 16-bit: pn_neg computes 0 - (-32768) in HL;
    #                          0 - (-32768) = 32768 which fits in unsigned 16-bit)
    # -----------------------------------------------------------------------
    pn_cases = [
        ("0",       0),
        ("42",      42),
        ("-7",      -7),
        ("12345",   12345),
        ("32767",   32767),
        ("-32768",  -32768),
    ]

    for label, value in pn_cases:
        # DE holds the value; negative values use two's complement in 16 bits.
        de_val = value & 0xFFFF
        out = m.capture_chput()
        m.call("print_number", de=de_val)
        got = bytes(out)
        want = expected_number(value)
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  print_number({label:7})  -> "
              f"{got!r}" + ("" if ok else f"   want {want!r}"))

    print()
    print("ALL PASS — print_number and print_crlf match the documented MSX integer format"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
