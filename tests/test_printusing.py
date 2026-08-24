# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BASIC-ROM PRINT USING format engine (printusing.asm), no emulator.

PRINT USING's outer driver (ex_print_using) is woven into the statement
interpreter (it walks the token cursor, calls eval/str_eval per value, cycles the
format), so it belongs to the openMSX differential probe (basic_probe_printusing.py,
oracle-validated byte-for-byte against a VG-8020). What IS a clean unit under test
here is the *format engine* — the leaf routines that turn one value + one field
spec into output characters:

  * pu_fmt_int   — signed-16 -> NUMBUF "[-]digits",0  (pure; no BIOS)
  * pu_do_number — eval -> right-justified in PU_W, '%' on overflow (CHPUT capture,
                   eval stubbed to inject the value)
  * pu_do_string — str_eval -> '&' whole / '!' first char / '\\..\\' fixed-width
                   (CHPUT capture, str_eval stubbed to inject the string)

These are exactly the routines whose HL-clobber bugs the probe caught during
development; locking them in as a fast emulator-free regression guards the fix.

Oracle basis (each expected value independently derivable, never from the ROM):
  * digits: base-10 arithmetic (Python str()).
  * field framing (right-justify pad, '%' overflow, left-justify+space-pad,
    '!'=first char, '&'=whole): the documented MSX-BASIC PRINT USING field
    semantics, cited in printusing.asm's module header.
"""

import os
from _tmp import tp
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

ROM = tp("zb_printusing.rom")
SYM = tp("zb_printusing.sym")
SBUF  = 0xC200           # scratch [len][ptr] descriptor for the string cases
SBODY = 0xC240           # the body those descriptors point at


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    NUMBUF = m.sym["NUMBUF"]
    STRPTR = m.sym["STRPTR"]
    fails = 0

    def report(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:28} -> "
              f"{got!r}" + ("" if ok else f"   want {want!r}"))

    # -----------------------------------------------------------------------
    # pu_fmt_int: DE (signed 16) -> NUMBUF "[-]digits",0 ; returns B = length.
    # Oracle: base-10 arithmetic + the '-' sign rule (printusing.asm pu_fmt_int).
    # -----------------------------------------------------------------------
    for value in (0, 5, 42, -7, 12345, 32767, -32768):
        # poison only NUMBUF's own 8 bytes ($E0C0..$E0C7) — STRPTR/PRDEST live
        # just above it, so a wider fill would clobber the PRINT destination.
        m.mem[NUMBUF:NUMBUF + 8] = b"\xee" * 8
        cpu = m.call("pu_fmt_int", de=value & 0xFFFF)
        want = str(value).encode("ascii")
        # text is the bytes up to the 0 terminator
        end = m.mem.index(0, NUMBUF)
        got = bytes(m.mem[NUMBUF:end])
        report(f"pu_fmt_int({value})", got, want)
        # B must equal the digit-string length (derived independently)
        report(f"pu_fmt_int({value}).len", cpu.b, len(want))

    # -----------------------------------------------------------------------
    # pu_do_number: eval the value, emit right-justified in PU_W; '%' + full
    # number on overflow. eval is stubbed to inject DE; CHPUT capture is output.
    # Oracle: documented '#'-field justification (printusing.asm header).
    #   width >= len  -> (width-len) spaces then the digits
    #   width <  len  -> '%' then the full number (MSX overflow marker)
    # -----------------------------------------------------------------------
    def num_case(value, width, want):
        m.trap("eval", lambda mm, v=value: setattr(mm.cpu, "de", v & 0xFFFF))
        m.poke(m.sym["PU_W"], width)
        out = m.capture_chput()
        m.call("pu_do_number")
        report(f"PRINT USING #*{width} ; {value}", bytes(out), want)

    num_case(42, 5, b"   42")     # right-justified, 3 leading spaces
    num_case(42, 2, b"42")        # exact fit
    num_case(-7, 4, b"  -7")      # '-' counts as a position
    num_case(12345, 3, b"%12345")  # overflow -> '%' + full number
    num_case(0, 3, b"  0")        # zero is one digit

    # -----------------------------------------------------------------------
    # pu_do_string: str_eval the value, emit per PU_TYPE. str_eval is stubbed to
    # point STRPTR at a [len][bytes] descriptor in scratch RAM and set CF (=is
    # string). CHPUT capture is the output.
    # Oracle: documented string fields (printusing.asm header):
    #   type 1 '&'    -> the whole string
    #   type 2 '!'    -> the first character (empty -> nothing)
    #   type 3 '\\..\\' -> left-justified in PU_W, space-padded, truncated if longer
    # -----------------------------------------------------------------------
    def str_case(label, text, ptype, width, want):
        # ⚠️ THE DESCRIPTOR IS [len][ptr], NOT [len][bytes].
        # The lean build stored a string value's bytes INLINE after the length;
        # the shipped str-engine build stores a POINTER to a heap body, and
        # pu_deref_body (str-engine.asm) is what every reader goes through. This
        # test seeded the lean shape and ran on the lean build until S3
        # (docs/spec-lean-retire-s3-gates.md §5, F-U), so it never saw the
        # difference. Body goes in its own buffer; the descriptor points at it.
        s = text.encode("ascii")
        m.mem[SBODY:SBODY + len(s)] = s
        m.mem[SBUF] = len(s)
        m.poke_w(SBUF + 1, SBODY)

        def stub(mm):
            mm.poke_w(STRPTR, SBUF)
            mm.cpu.f |= 0x01        # CF set -> str_eval found a string
        m.trap("str_eval", stub)
        m.poke(m.sym["PU_TYPE"], ptype)
        m.poke(m.sym["PU_W"], width)
        out = m.capture_chput()
        m.call("pu_do_string")
        report(label, bytes(out), want)

    str_case("PRINT USING &     ; 'HELLO'", "HELLO", 1, 0, b"HELLO")
    str_case("PRINT USING !     ; 'HELLO'", "HELLO", 2, 0, b"H")
    str_case("PRINT USING !     ; ''",      "",      2, 0, b"")
    str_case("PRINT USING \\...\\ ; 'HI'",    "HI",    3, 5, b"HI   ")  # pad to 5
    str_case("PRINT USING \\.\\  ; 'HELLO'",  "HELLO", 3, 3, b"HEL")    # truncate

    print()
    print("ALL PASS — PRINT USING engine matches the documented field semantics"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
