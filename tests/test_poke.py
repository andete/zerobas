# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BASIC-ROM `do_poke` (POKE statement), no emulator.

POKE is a Tier-1 routine — pure RAM write, no BIOS, no I/O — so nothing is
stubbed.  We hand-build a token stream for the two operands (address, value),
place it in RAM, point HL there, and call do_poke.  On success the handler
writes mem[addr] = val_lo and falls through to exec_stmt with HL on the
trailing 0x00 terminator; exec_stmt returns immediately (it RETurns when HL
holds 0x00 — its end-of-line guard), so the harness sees a clean return.

Entry convention: exec_stmt dispatches to ex_poke which does `inc hl` (past
the POKE token) then `jp do_poke`.  do_poke therefore enters with HL already
pointing at the first operand token — no keyword token in the buffer.

Oracle basis (poke.asm):
  do_poke calls eval twice (addr -> DE, then value -> DE) and writes the low
  byte of the second result to the address given by the first.  Both operands
  are full 16-bit integer expressions decoded by eval.  The MSX-BASIC language
  reference specifies POKE writes the low byte of value to addr.

Token encoding (sysvars.inc / spec-tokens-statements.md):
  &Hxxxx -> HEX_TOKEN ($0C), lo byte, hi byte   (eval decodes this exactly)
  Digit 0..9 -> INT_DIGIT_BASE+n ($11+n)         (one byte, no extra bytes)
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

ROM = "/tmp/zb_io.rom"
SYM = "/tmp/zb_io.sym"
BUF = 0xC000   # scratch token buffer (free RAM, below BLOAD region)


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def hex_tok(v):
    """Return the 3-byte HEX_TOKEN encoding for a 16-bit value v."""
    return bytes([0x0C, v & 0xFF, (v >> 8) & 0xFF])


def digit_tok(n):
    """Return the 1-byte digit token for 0..9."""
    assert 0 <= n <= 9
    return bytes([0x11 + n])


def run_poke(m, addr_tokens, val_tokens):
    """Place operand tokens in BUF and call do_poke with HL=BUF.

    The stream is: <addr_tokens> , <val_tokens> 0x00
    exec_stmt (jumped-to at the end) sees 0x00 -> ret z immediately.
    """
    stream = addr_tokens + b',' + val_tokens + b'\x00'
    m.poke(BUF, stream)
    m.call("do_poke", hl=BUF)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)

    cases = [
        # (addr, value, description)
        (0xC200, 0x42, "hex addr, hex val"),
        (0xC300, 0xFF, "hex addr, max byte value"),
        (0xC400, 0x00, "hex addr, zero value"),
        (0xC500, 0x01, "hex addr, digit val 1 (digit token)"),
    ]

    fails = 0
    for addr, val, desc in cases:
        # Zero the target address first so a stale byte cannot give a false PASS
        m.mem[addr] = 0xAA   # sentinel: confirm the write actually happened

        addr_toks = hex_tok(addr)
        # For val: use digit token for 0..9 to exercise both token kinds
        if 0 <= val <= 9:
            val_toks = digit_tok(val)
        else:
            val_toks = hex_tok(val)

        run_poke(m, addr_toks, val_toks)

        got = m.mem[addr]
        want = val & 0xFF     # POKE writes the low byte (MSX-BASIC language ref)
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  POKE &H{addr:04X},{val:#04x}"
              f" -> mem[{addr:#06x}]={got:#04x}"
              + ("" if ok else f"   want {want:#04x}")
              + f"  ({desc})")

    # --- error path: missing comma -> poke_err -> stmt_error -----------------
    # poke.asm: if ',' is absent, jr z,poke_err pops the saved address and
    # calls stmt_error, which writes ERRMARK=$DD and prints an error string.
    # We confirm ERRMARK is set (observable; no comma in the stream).
    m.mem[m.sym["ERRMARK"]] = 0x00          # clear first
    m.capture_chput()                       # absorb any error-string output
    # ⚠️ SAMPLE ERRMARK AT THE ABORT FUNNEL, NOT AFTER THE CALL RETURNS.
    # This used to `try: m.call(...) except: pass` and read ERRMARK afterwards --
    # but the funnel does `ld sp,(SAVSTK)`, and SAVSTK is 0 in this harness's
    # zeroed RAM, so its tail `ret` popped from $0000 and the CPU ran away
    # through memory until msxtest's 2,000,000-step guard fired. The assertion
    # was therefore reading "whatever ERRMARK held after 2M steps of executing
    # the ROM from an arbitrary entry point", which happened to still be $DD.
    # D-CONTR (docs/spec-basic-cont-record.md) shifted page 1 by 19 bytes, the
    # runaway landed on `ex_goto_undef` instead, and the row went red with
    # ERRMARK=$DB -- a REAL failure of the apparatus, not of do_poke.
    # 🔴 AND IT IS NOT EVEN A FUNCTION OF THE BUILD ALONE. Re-sampled the OLD way
    # on ONE fixed build, this case reads $DB after the four POKE cases above and
    # $3A on its own -- the runaway walks different memory. The assertion was
    # never measuring stmt_error; it was measuring where 2M steps happened to
    # land, and it agreed for the wrong reason for as long as it did.
    # Trapping fre_abort_low samples the byte at the one moment the test is
    # actually about, and removes the runaway entirely: poke_err reaches it via
    # `jp stmt_error` -> `jp raise_error` -> ... -> `jp fre_abort_low` with no
    # intervening frame, so the trap's RET goes straight back to m.call's
    # sentinel. No except-guard: a genuine runaway must now be LOUD.
    seen = []
    m.trap("fre_abort_low", lambda mm: seen.append(mm.mem[mm.sym["ERRMARK"]]))
    bad_stream = hex_tok(0xC600) + b'\x00'  # addr token then EOL (no comma, no value)
    m.poke(BUF, bad_stream)
    m.call("do_poke", hl=BUF)
    errmark = seen[0] if seen else None
    ok = errmark == 0xDD   # stmt_error always sets ERRMARK=$DD (interp.asm)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  POKE missing comma -> ERRMARK="
          f"{'<funnel never reached>' if errmark is None else f'{errmark:#04x}'}"
          f" (want 0xdd = stmt_error sentinel, sampled AT fre_abort_low)")

    print()
    print("ALL PASS — do_poke writes mem[addr]=val_lo for all cases"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
