# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: assorted statement front-ends run through the executor, no emulator.

Covers the statement handlers reached via the dispatcher that the other tests
bypass by calling internals directly:
  - PRINT  (ex_print + exp_* + print_number) — captured CHPUT stream
  - GOTO   (ex_goto, the bare statement form)
  - CLEAR  (ex_clear / clr_himem — records HIMEM)
  - WIDTH  (ex_width — sets LINLEN, re-inits via CHGMOD)

Method: store a small program, run it through run_prog (so each statement goes
through exec -> exec_stmt -> the handler), trap BREAKX (never pressed) and the
screen BIOS, capture CHPUT, then assert on the captured output / variables /
sysvars.

Oracle: documented MSX-BASIC PRINT formatting (leading space + digits + trailing
space; ';' joins with no spacing; CR/LF ends the line unless a trailing
separator suppresses it), GOTO control flow, and the CLEAR/WIDTH side effects
documented in clear.asm / screen.asm — not the ROM's own output.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = "/tmp/zb_stmt.rom"
SYM = "/tmp/zb_stmt.sym"
SRC = 0xC000
TOKB = 0xC100


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def run_prog_cap(m, lines):
    """Run a program, capturing the CHPUT stream; screen BIOS stubbed out."""
    m.trap("BREAKX", lambda mm: setattr(mm.cpu, "f", mm.cpu.f & ~0x01))
    for b in ("CHGMOD", "CHGCLR", "CLS", "ERAFNK", "DSPFNK"):
        m.trap(b, lambda mm: None)
    out = m.capture_chput()
    m.call("new_prog")
    for lineno, body in lines:
        m.poke(SRC, body.encode("ascii") + b"\x00")
        m.mem[TOKB:TOKB + 192] = b"\x00" * 192
        m.call("tokenise", hl=SRC, de=TOKB)
        m.call("store_line", bc=lineno, hl=TOKB)
    m.call("run_prog")
    return bytes(out)


def var(m, name):
    return m.call("var_get_key", b=ord(name), c=0).de


def run():
    build()
    fails = 0

    def check(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}: got {got!r}"
              + ("" if ok else f"  want {want!r}"))

    # --- PRINT (ex_print): documented MSX integer format + separators --------
    # Non-negative number: leading space (sign slot) + digits + trailing space.
    check("PRINT 42", run_prog_cap(Machine(ROM, SYM), [(10, "PRINT 42")]),
          b" 42 \r\n")
    # String literal printed verbatim, then CR/LF.
    check('PRINT "HI"', run_prog_cap(Machine(ROM, SYM), [(10, 'PRINT "HI"')]),
          b"HI\r\n")
    # ';' joins with no extra spacing (each number keeps its own framing).
    # Regression for the print_number HL-clobber bug: items after the first
    # numeric one must still print (exp_num now guards the token cursor).
    check("PRINT 1;2", run_prog_cap(Machine(ROM, SYM), [(10, "PRINT 1;2")]),
          b" 1  2 \r\n")
    check("PRINT 1;2;3", run_prog_cap(Machine(ROM, SYM), [(10, "PRINT 1;2;3")]),
          b" 1  2  3 \r\n")
    # number followed by a string literal (cursor survives the number -> string).
    check('PRINT 7;"HI"', run_prog_cap(Machine(ROM, SYM), [(10, 'PRINT 7;"HI"')]),
          b" 7 HI\r\n")
    # Trailing ';' suppresses the closing newline.
    check('PRINT "X";', run_prog_cap(Machine(ROM, SYM), [(10, 'PRINT "X";')]),
          b"X")
    # Bare PRINT prints an empty line.
    check("PRINT (bare)", run_prog_cap(Machine(ROM, SYM), [(10, "PRINT")]),
          b"\r\n")

    # --- GOTO (ex_goto, bare statement form) ---------------------------------
    m = Machine(ROM, SYM)
    run_prog_cap(m, [(10, "GOTO 30"), (20, "A=1"), (30, "A=2")])
    check("GOTO skips line 20 (A)", var(m, "A"), 2)

    # --- CLEAR ,<himem> (ex_clear / clr_himem records HIMEM) -----------------
    m = Machine(ROM, SYM)
    run_prog_cap(m, [(10, "CLEAR ,&HABCD")])
    himem = m.mem[m.sym["HIMEM"]] | (m.mem[m.sym["HIMEM"] + 1] << 8)
    check("CLEAR ,&HABCD sets HIMEM", himem, 0xABCD)

    # --- WIDTH n (ex_width sets LINLEN) --------------------------------------
    m = Machine(ROM, SYM)
    run_prog_cap(m, [(10, "WIDTH 32")])
    check("WIDTH 32 sets LINLEN", m.mem[m.sym["LINLEN"]], 32)

    print()
    print("ALL PASS — PRINT/GOTO/CLEAR/WIDTH match documented statement behaviour"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
