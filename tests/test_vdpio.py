# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BASIC-ROM `do_vpoke` (VPOKE) and `do_out` (OUT), no emulator.

do_vpoke — Tier-2: calls WRTVRM BIOS to write to VRAM.  We trap WRTVRM and
assert it is called with HL = VRAM address and A = value (the documented
WRTVRM contract from the MSX Assembly Page / MSX2 Technical Handbook).

do_out — Tier-2 (I/O): executes a raw Z80 `out (c),a` instruction to write a
byte to an I/O port.  We capture it with m.record_out() (which registers a
cpu.io_out callback) and assert the logged (port, value) tuple.

Entry convention (vdpio.asm): exec_stmt dispatches via ex_vpoke / ex_out, each
of which does `inc hl; jp do_vpoke / do_out`.  So do_vpoke / do_out are entered
with HL already pointing at the first operand token (past the keyword token).
Token stream layout: <addr_tokens> , <val_tokens> 0x00

exec_stmt terminates cleanly when HL holds 0x00 (it does `ret z`), so no trap
on exec_stmt is required.

Oracle basis (vdpio.asm):
  do_vpoke: eval -> DE = VRAM addr; skip comma; eval -> DE = value;
            A = E (low byte); BC = VRAM addr; HL = BC; call WRTVRM.
  do_out:   eval -> DE = port; skip comma; eval -> DE = value;
            BC = port; A = E (low byte); out (c), a.
  WRTVRM contract (MSX2 TH / MSX Assembly Page): write A to VRAM[HL].
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = "/tmp/zb_io.rom"
SYM = "/tmp/zb_io.sym"
BUF = 0xC000   # scratch token buffer


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def hex_tok(v):
    """3-byte HEX_TOKEN ($0C lo hi) encoding for a 16-bit value."""
    return bytes([0x0C, v & 0xFF, (v >> 8) & 0xFF])


def digit_tok(n):
    """1-byte digit token ($11+n) for 0..9."""
    assert 0 <= n <= 9
    return bytes([0x11 + n])


def run():
    build()
    m = Machine(ROM, SYM)
    s = m.sym

    fails = 0

    # =========================================================================
    # do_vpoke: VPOKE addr,val -> WRTVRM(HL=addr, A=val)
    # =========================================================================
    # WRTVRM is the documented BIOS write-to-VRAM entry (MSX2 TH / MSX Assembly
    # Page: HL = VRAM address, A = byte to write).  vdpio.asm sets HL = BC =
    # the VRAM address obtained from eval, and A = E = the low byte of the value
    # from the second eval, then calls WRTVRM.  We record HL and A on each entry.

    vpoke_cases = [
        # (vram_addr, value, description)
        (0x0000, 0x00, "VRAM addr 0, val 0"),
        (0x1800, 0x20, "VRAM addr 0x1800 (typical name table), space char"),
        (0x3FFF, 0xAB, "VRAM addr max TMS9918 (0x3FFF), arbitrary val"),
        (0x0100, 0x07, "VRAM addr 0x100, digit val 7 (digit token)"),
    ]

    for vram, val, desc in vpoke_cases:
        log = m.record("WRTVRM", regs=("hl", "a"))
        addr_toks = hex_tok(vram)
        val_toks = digit_tok(val) if 0 <= val <= 9 else hex_tok(val)
        stream = addr_toks + b',' + val_toks + b'\x00'
        m.poke(BUF, stream)
        m.call("do_vpoke", hl=BUF)
        got_hl = log[0]["hl"] if log else None
        got_a  = log[0]["a"]  if log else None
        ok = len(log) == 1 and got_hl == vram and got_a == (val & 0xFF)
        fails += not ok
        hl_s = f"{got_hl:#06x}" if got_hl is not None else "??"
        a_s  = f"{got_a:#04x}"  if got_a  is not None else "??"
        print(f"{'PASS' if ok else 'FAIL'}  VPOKE {vram:#06x},{val:#04x}"
              f" -> WRTVRM(HL={hl_s}, A={a_s})"
              f"  ({desc})")

    # =========================================================================
    # do_out: OUT port,val -> out (c),val_lo  [captured by record_out()]
    # =========================================================================
    # vdpio.asm: eval -> DE = port; BC = port; A = low byte of value; out (c),a.
    # The Z80 `out (c),a` instruction uses C as the port address and A as the
    # data byte.  record_out() captures (port, val) tuples via cpu.io_out.

    out_cases = [
        # (port, value, description)
        (0x98, 0x00, "VDP data port write, val 0 (digit token)"),
        (0x99, 0x80, "VDP ctrl port write"),
        (0xA8, 0x01, "PPI port A write (slot select)"),
        (0x00, 0x05, "port 0, digit val 5"),
    ]

    for port, val, desc in out_cases:
        log = m.record_out()
        port_toks = hex_tok(port)
        val_toks = digit_tok(val) if 0 <= val <= 9 else hex_tok(val)
        stream = port_toks + b',' + val_toks + b'\x00'
        m.poke(BUF, stream)
        m.call("do_out", hl=BUF)
        # record_out logs (port, val) tuples; port is the C register (16-bit BC
        # from eval, but `out (c),a` uses C = low byte as the port number).
        # The io_out callback receives (port, val) where port = C register value.
        found = any(p == (port & 0xFF) and v == (val & 0xFF)
                    for p, v in log)
        ok = found and len(log) >= 1
        detail = log[0] if log else None
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  OUT {port:#04x},{val:#04x}"
              f" -> io_out{detail!r}"
              f"  ({desc})")

    print()
    print("ALL PASS — do_vpoke calls WRTVRM(HL,A) and do_out issues OUT(port,val)"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
