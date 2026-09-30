# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: console INPUT / LINE INPUT — the BIOS-independent core (repack build).

basic/input.asm's console handler is assembled ONLY in the repack build
(ROM_BASE < $4000), so this builds basic/main-reloc.asm (ROM_BASE=$2812) and loads it
at that base — the lean build has no console INPUT by design.

The full statement (prompt printing, read_line, var assignment) needs the keyboard +
the screen, which is the openMSX oracle probe's job (basic_probe_input.py). What is
pure in-RAM logic and fully testable here — the genuinely new code the slice added:

  * (RETIRED 2026-09-29, D-INPNUM) input_num_field — a 16-bit INTEGER validator whose
    contract this file used as its oracle: `1 2`, `3.5`, empty, `+`, `-` and blanks
    all "invalid". The references MEASURED every one of those as accepted (12, 3.5,
    0, 0, 0, 0 -- scratchpad/inpnum_run.out, inpnum_run2.out), and 40000 wrapped to
    -25536. Its replacement `inp_num` parses through the sub-ROM (strheap op 19, a
    CALSLT this host sim does not run), so its oracle is the emulator differential:
    scratchpad/inpnum_probe.py and kwsweep rows `input_flt` / `inputnum`.
  * (D-CHANSWITCH) a NUMERIC INPUT # item is read in the seqio tenant (sub-ROM,
    sq_numitem) because its rules need a PEEK -- `" 1  2 "` leaves "2 " for the next
    read. D-INPNUM's first cut, a numeric mode of read_into_strscr tested here for a
    day, left the trailing " \r\n" and read `1 0 2 0`; its oracle is now the emulator
    rows `inputnum` / `inputnum2` / `chanfor`.
  * linebuf_getbyte — the ARL_GETBYTE byte-source vector for a console line: next
    LINEBUF byte, advance INP_CURSOR, CF set (EOF) at the 0 terminator WITHOUT
    advancing (the same end contract fat_io_getbyte / cas_in_getbyte present).
  * inpc_more_input — "is another field available?" — ZF=1 iff the last field the
    splitter consumed ended on a ',' (drives the ?extra ignored / too-few decision).
  * the field split itself — read_into_strscr driven through linebuf_getbyte, sharing
    the file forms' exact splitter/STRMAX clamp/STRSCR descriptor.

Oracle basis (independently derivable, never the ROM's own output):
  * signed-int16 decimal parse with strict trailing-junk rejection — the documented
    INPUT numeric-field contract (integer engine, VAL's own integer stance).
  * the field/line split at ','/CR/EOF — read_into_strscr's documented contract
    (files.asm), shared with INPUT#.
"""

import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry, zero  # noqa: E402

ROM = tp("zb_input.rom")
SYM = tp("zb_input.sym")
RELOC_BASE = 0x2812


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=RELOC_BASE)
    s = m.sym

    STRSCR = s["STRSCR"]
    LINEBUF = s["LINEBUF"]
    INP_CURSOR = s["INP_CURSOR"]
    ARL_GETBYTE = s["ARL_GETBYTE"]
    FCH_RDMODE = s["FCH_RDMODE"]

    fails = 0

    def report(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:36} -> {got!r}"
              + ("" if ok else f"   want {want!r}"))

    def s16(v):
        return v - 0x10000 if v >= 0x8000 else v

    # -----------------------------------------------------------------------
    # linebuf_getbyte: next LINEBUF byte, advance INP_CURSOR; CF at the 0
    # terminator without advancing. Oracle: the fat_io_getbyte end contract.
    # -----------------------------------------------------------------------
    def lgb_sequence(line):
        """Drive linebuf_getbyte from cursor 0 to EOF; return the bytes it yields
        and the final cursor value."""
        m.poke(LINEBUF, line + b"\x00")
        m.poke(INP_CURSOR, 0)
        out = []
        for _ in range(len(line) + 2):
            cpu = m.call("linebuf_getbyte")
            if carry(cpu):
                break
            out.append(cpu.a & 0xFF)
        return bytes(out), m.mem[INP_CURSOR]

    seq, cur = lgb_sequence(b"12,AB")
    report("lgb yields '12,AB'", seq, b"12,AB")
    report("lgb cursor at terminator", cur, 5)     # left ON the 0 (index 5)
    # EOF is idempotent + does not advance
    m.poke(LINEBUF, b"\x00")
    m.poke(INP_CURSOR, 0)
    cpu = m.call("linebuf_getbyte")
    report("lgb empty line -> CF", carry(cpu), True)
    report("lgb empty line cursor unmoved", m.mem[INP_CURSOR], 0)

    # -----------------------------------------------------------------------
    # Field split: read_into_strscr driven through linebuf_getbyte (FCH_RDMODE=0
    # field, =1 line). This is the shared INPUT# splitter re-pointed at the
    # console line. Oracle: split at ','/CR/EOF (read_into_strscr contract).
    # -----------------------------------------------------------------------
    def strscr_val():
        n = m.mem[STRSCR]
        return bytes(m.mem[STRSCR + 1:STRSCR + 1 + n])

    def setup_line(line):
        m.poke(LINEBUF, line + b"\x00")
        m.poke(INP_CURSOR, 0)
        m.poke_w(ARL_GETBYTE, s["linebuf_getbyte"])

    def read_field(mode):
        m.poke(FCH_RDMODE, mode)
        m.call("read_into_strscr")
        return strscr_val()

    # field mode (0): "12,AB,X" -> "12", "AB", "X" across three calls
    setup_line(b"12,AB,X")
    report("field 1 of '12,AB,X'", read_field(0), b"12")
    report("field 2 of '12,AB,X'", read_field(0), b"AB")
    report("field 3 of '12,AB,X'", read_field(0), b"X")

    # inpc_more_input after each field: ZF=1 iff the last field ended on a ','.
    # Re-walk the line, checking the flag between fields.
    setup_line(b"7,9")
    read_field(0)                                  # consume "7" (comma-terminated)
    report("more_input after '7,' -> ZF", zero(m.call("inpc_more_input")), True)
    read_field(0)                                  # consume "9" (EOF-terminated)
    report("more_input after '9'(eof) -> ZF", zero(m.call("inpc_more_input")), False)

    # an empty line: cursor never advanced -> no more input (guards the too-few path)
    m.poke(LINEBUF, b"\x00")
    m.poke(INP_CURSOR, 0)
    report("more_input empty line -> ZF", zero(m.call("inpc_more_input")), False)

    # line mode (1): commas are DATA, whole line is one field (LINE INPUT)
    setup_line(b"12,AB,X")
    report("line mode whole line", read_field(1), b"12,AB,X")

    # a leading space is preserved as a value byte in line mode (LINE INPUT keeps it)
    setup_line(b" hello")
    report("line mode keeps leading space", read_field(1), b" hello")

    print()
    print("ALL PASS — console INPUT core (linebuf source, field/line split) matches contract"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
