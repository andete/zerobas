# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BASIC-ROM `ex_def` (DEF USR) and `ev_usr` (USR() call), no emulator.

ex_def — statement handler for `DEF USR[n] = <addr>`.  Entered with HL on the
DEF token; does `inc hl` itself.  On success writes the 16-bit address into
USRTAB[n*2] (2 bytes, little-endian).  We assert the memory at the correct
USRTAB slot holds the address we gave.

ev_usr — expression-factor handler for `USR[n](arg)`.  Uses IX as cursor
(expr.asm convention); entered with IX on the USR token.  Evaluates the
argument expression into DE, loads the vector from USRTAB, and jumps to the
routine with the argument in DAC+2..3, VALTYP 2 and HL = DAC (the published
convention, D-ADDR29 DAC 2026-09-25; it was HL = argument).  We trap the target
address to catch the call and
verify that HL contains the argument.

Token stream details (sysvars.inc / usr.asm):
  DEF_TOKEN  = $97   USR_TOKEN = $DD   EQ_TOKEN  = $EF
  INT_DIGIT_BASE = $11  (digit n -> $11+n)
  HEX_TOKEN  = $0C,lo,hi  (for 16-bit addresses)
  USR number 0..9 as digit token $11+n; absent = default USR0.

USRTAB layout (sysvars.inc): USRTAB=$F39A, 10 slots of 2 bytes LE.
  Slot n is at USRTAB + n*2; low byte first (Z80 LE).

Entry conventions:
  ex_def: HL on the DEF token (exec_stmt jumps directly; handler does inc hl).
  ev_usr: IX on the USR token (called from expr.asm's factor dispatcher).

Calling convention for ev_usr (usr.asm comment):
  zerobas passes the 16-bit integer argument in HL (own design, not the
  DAC/VALTYP protocol of the reference ROM).  The called routine's HL is the
  argument; its RET returns to usr_ret which copies HL -> DE as the result.

Source bug note: none found.  Uncertainties:
  - If the USR routine at the trap address modifies HL before returning, the
    recorded HL in the trap is the entry value — this is the intended argument
    (pre-modification), which is what we assert.
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
BASIC_BASE = 0x2765

ROM = tp("zb_io.rom")
SYM = tp("zb_io.sym")
BUF  = 0xC000   # token buffer for ex_def
IBUF = 0xC100   # IX-cursor token buffer for ev_usr


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def hex_tok(v):
    """3-byte HEX_TOKEN encoding for a 16-bit value."""
    return bytes([0x0C, v & 0xFF, (v >> 8) & 0xFF])


def digit_tok(n):
    """1-byte digit token ($11+n) for 0..9."""
    assert 0 <= n <= 9
    return bytes([0x11 + n])


def run():
    build()
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    s = m.sym

    # Zero the USR table so stale values don't mask failures
    m.poke(s["USRTAB"], bytes(20))

    fails = 0

    # =========================================================================
    # ex_def: DEF USR[n] = <addr>  stores addr at USRTAB[n*2]
    # =========================================================================
    # Token stream (BUF):
    #   [ DEF_TOKEN | USR_TOKEN | <digit_n or nothing> | EQ_TOKEN | hex_tok(addr) | 0x00 ]
    # exec_stmt ends when HL reaches 0x00 (ret z guard).
    #
    # USRTAB slot for USR n: USRTAB + n*2 (little-endian 16-bit address).
    # Oracle: usr.asm usr_setslot stores low byte then high byte.

    def_cases = [
        # (usr_index, use_explicit_digit, target_addr, description)
        (0, True,  0x9000, "DEF USR0=&H9000 (explicit 0)"),
        (1, True,  0xA000, "DEF USR1=&HA000"),
        (5, True,  0xB800, "DEF USR5=&HB800"),
        (0, False, 0x8100, "DEF USR=&H8100 (implicit USR0)"),
    ]

    for idx, explicit, addr, desc in def_cases:
        m.poke(s["USRTAB"], bytes(20))   # re-zero before each case
        if explicit:
            stream = bytes([s["DEF_TOKEN"], s["USR_TOKEN"], 0x11 + idx,
                            s["EQ_TOKEN"]]) + hex_tok(addr) + b'\x00'
        else:
            # No digit after USR -> usr_index defaults to 0
            stream = bytes([s["DEF_TOKEN"], s["USR_TOKEN"],
                            s["EQ_TOKEN"]]) + hex_tok(addr) + b'\x00'
        m.poke(BUF, stream)
        m.call("ex_def", hl=BUF)

        slot = s["USRTAB"] + idx * 2
        got_lo = m.mem[slot]
        got_hi = m.mem[slot + 1]
        got_addr = got_lo | (got_hi << 8)
        ok = got_addr == addr
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {desc}"
              f" -> USRTAB[{idx}]={got_addr:#06x}  (want {addr:#06x})")

    # =========================================================================
    # ev_usr: USR[n](arg) calls the stored vector with HL = arg
    # =========================================================================
    # ev_usr is the expression-factor entry and uses IX as cursor.
    # Token stream (IBUF): [ USR_TOKEN | '(' | <arg_tokens> | ')' ]
    # No trailing 0x00 needed here — ev_usr does not fall into exec_stmt.
    #
    # Setup:
    #   1. Set a known DEF USR address via direct USRTAB poke.
    #   2. Trap that address to capture HL on entry.
    #   3. Call ev_usr with IX = IBUF.
    #   4. Assert trap fired with HL = arg.
    #
    # ev_usr dispatch: after parsing and evaluating the argument into DE,
    # usr_call is reached.  usr_call does:
    #   ld c,(hl); inc hl; ld b,(hl)  ; BC = USRTAB slot value
    #   ex de,hl                       ; HL = argument
    #   push de (=usr_ret); push bc; ret   ; jumps to BC
    # The trap fires when cpu.pc == target.  cpu.hl at that point = argument.
    #
    # We pick a safe address in the page-3 RAM region ($C200) that doesn't
    # overlap our buffers.  On the trap the harness pops usr_ret from the stack
    # and continues execution from there (ex de,hl; pop ix; ret -> SENTINEL).

    TARGET = 0xC200   # safe free-RAM address for the trap target

    usr_call_cases = [
        # (usr_index, use_explicit, arg_val, description)
        (0, False, 0,    "USR(0) implicit USR0, arg=0"),
        (0, True,  7,    "USR0(7) digit arg"),
        (1, True,  0x1234, "USR1(&H1234) hex arg"),
        (3, True,  0xFF, "USR3(&HFF)"),
    ]

    for idx, explicit, arg, desc in usr_call_cases:
        # Write the target address into USRTAB[idx]
        m.poke(s["USRTAB"], bytes(20))
        slot = s["USRTAB"] + idx * 2
        m.mem[slot]     = TARGET & 0xFF
        m.mem[slot + 1] = (TARGET >> 8) & 0xFF

        # Capture the ENTRY state of the trapped routine: HL, A, and the
        # published DAC+2..3 / VALTYP (D-ADDR29 DAC, 2026-09-25 -- the HL-arg
        # convention this file used to assert is superseded by the reference's).
        captured = []
        def trap_fn(machine, captured=captured):
            dac = s["DAC"]
            captured.append((machine.cpu.hl, machine.cpu.a,
                             machine.mem[dac + 2] | (machine.mem[dac + 3] << 8),
                             machine.mem[s["VALTYP_PUB"]]))
        m.trap(TARGET, trap_fn)

        # Build IX-based token stream for ev_usr:
        #   [ USR_TOKEN | [digit_n if explicit] | '(' | arg_tokens | ')' ]
        if explicit:
            idx_bytes = bytes([0x11 + idx])
        else:
            idx_bytes = b''
        if 0 <= arg <= 9:
            arg_toks = digit_tok(arg)
        else:
            arg_toks = hex_tok(arg)
        stream = (bytes([s["USR_TOKEN"]]) + idx_bytes +
                  b'(' + arg_toks + b')')
        m.poke(IBUF, stream)
        cpu = m.call("ev_usr", ix=IBUF)

        # entry: HL = DAC, A = VALTYP = 2, the argument at DAC+2..3;
        # return: a routine that leaves DAC alone returns the argument (the
        # reference's bare-RET answer, scratchpad/usrdac_probe.py)
        want = (s["DAC"], 2, arg, 2)
        ok = len(captured) == 1 and captured[0] == want and cpu.de == arg
        fails += not ok
        got = captured[0] if captured else None
        got_s = ("HL=%#06x A=%d DAC+2=%#06x VALTYP=%d" % got) if got else "??"
        print(f"{'PASS' if ok else 'FAIL'}  {desc}"
              f" -> trap fired {len(captured)} time(s), {got_s}, result DE={cpu.de:#06x}"
              f"  (want HL=DAC, A=2, DAC+2={arg:#06x}, VALTYP=2, result {arg:#06x})")

    # =========================================================================
    # ev_usr with un-DEF'd vector: ERRMARK=$DD, returns DE=0
    # =========================================================================
    # usr_call: if BC=0 (un-DEF'd), jumps to usr_undef which sets ERRMARK=$DD
    # and returns DE=0 without jumping to user code.
    m.poke(s["USRTAB"], bytes(20))   # all slots zero
    m.mem[s["ERRMARK"]] = 0x00
    stream = bytes([s["USR_TOKEN"]]) + b'(' + digit_tok(0) + b')'
    m.poke(IBUF, stream)
    cpu = m.call("ev_usr", ix=IBUF)
    errmark = m.mem[s["ERRMARK"]]
    ok = errmark == 0xDD and cpu.de == 0
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  USR0(0) un-DEF'd"
          f" -> ERRMARK={errmark:#04x}, DE={cpu.de:#06x}"
          f"  (want ERRMARK=0xdd, DE=0)")

    print()
    print("ALL PASS — ex_def stores USR vector; ev_usr calls it with the argument in DAC"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
