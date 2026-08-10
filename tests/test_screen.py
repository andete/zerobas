# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BASIC-ROM screen verbs (SCREEN/COLOR/CLS/KEY), no emulator.

Tier-2 tests: the handlers call BIOS entry points (CHGMOD, CHGCLR, CLS,
ERAFNK, DSPFNK) that are trapped and replaced by Python stubs.  We assert
that zerobas calls each entry with the correct arguments and/or writes the
correct sysvar bytes, not that the BIOS entry itself does anything.

Entry convention (screen.asm): each handler is entered with HL ON its own
keyword token.  The first instruction of every handler is `inc hl` to step
past that token.  exec_stmt dispatches directly to ex_screen / ex_color /
ex_cls / ex_key without the intermediary `inc hl` wrapper used by ex_poke.

So the token buffer layout for each verb is:
    [ keyword_token | operand tokens... | 0x00 ]
HL = start of buffer (on the keyword token).

exec_stmt ends each handler with `jp exec_stmt`; exec_stmt sees 0x00 at HL
and does `ret z` immediately — no trap needed on exec_stmt.

Oracle basis for BIOS calls (sysvars.inc / MSX Assembly Page / MSX2 TH):
  CHGMOD ($005F): A = screen mode 0..3
  CHGCLR ($0062): A = current screen mode (read from SCRMOD sysvar); reads
                  FORCLR/BAKCLR/BDRCLR from their documented sysvar addresses.
  CLS    ($00C3): zero flag must be set on entry.
  ERAFNK ($00CC): erase the function-key line (KEY OFF).
  DSPFNK ($00CF): display the function-key line (KEY ON).

Sysvar addresses (sysvars.inc; used verbatim via m.sym):
  FORCLR=$F3E9, BAKCLR=$F3EA, BDRCLR=$F3EB, SCRMOD=$FCAF.
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
BUF = 0xC000   # scratch token buffer


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def hex_tok(v):
    """3-byte HEX_TOKEN encoding for a 16-bit value."""
    return bytes([0x0C, v & 0xFF, (v >> 8) & 0xFF])


def digit_tok(n):
    """1-byte digit token for 0..9."""
    assert 0 <= n <= 9
    return bytes([0x11 + n])


def run():
    build()
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    s = m.sym

    fails = 0

    # =========================================================================
    # ex_screen: SCREEN n -> CHGMOD(A=n)
    # =========================================================================
    # MSX2 TH / MSX Assembly Page: CHGMOD is called with A = the desired screen
    # mode.  screen.asm evaluates the mode argument into DE, checks D=0 and E<4,
    # then `ld a,e; push hl; call CHGMOD; pop hl`.
    # Token stream: [ SCREEN_TOKEN | digit_n | 0x00 ]
    for mode in range(4):   # MSX1 supports modes 0..3
        log = m.record("CHGMOD", regs=("a",))
        stream = bytes([s["SCREEN_TOKEN"], 0x11 + mode, 0x00])
        m.poke(BUF, stream)
        m.call("ex_screen", hl=BUF)
        ok_count = len(log) == 1 and log[0]["a"] == mode
        fails += not ok_count
        print(f"{'PASS' if ok_count else 'FAIL'}  SCREEN {mode}"
              f" -> CHGMOD(A={log[0]['a'] if log else 'never called'})"
              f"  (want A={mode})")

    # ex_screen with no mode argument (bare SCREEN) -> Missing operand, ERR 24.
    # 🔴 THIS ROW USED TO ASSERT THE OPPOSITE ("bare SCREEN -> no CHGMOD call",
    # i.e. a silent no-op) AND IT WAS THE ONLY THING IN THE TREE THAT DID.
    # D-SCRERR measured both references: an argument list that ENDS where a value
    # was required is Missing operand (docs/spec-basic-screenerr.md §2.2). The
    # old row passed because a no-op returns cleanly; the new contract goes
    # `jp z,loc_missing` -> `jp raise_error`, whose `ld sp,(SAVSTK)` funnel the
    # host harness cannot follow (SAVSTK is 0 in zeroed RAM -> the CPU runs
    # away). So sample AT the funnel, exactly as test_poke.py's ERRMARK row does
    # -- no except-guard, so a genuine runaway stays LOUD.
    log = m.record("CHGMOD", regs=("a",))
    raised = []
    m.trap("raise_error", lambda mm: raised.append(mm.cpu.a))
    stream = bytes([s["SCREEN_TOKEN"], 0x00])    # bare SCREEN, no operand
    m.poke(BUF, stream)
    m.call("ex_screen", hl=BUF)
    ok = raised == [24] and len(log) == 0
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  SCREEN (bare) -> ERR 24 Missing operand,"
          f" CHGMOD not called  (raise_error saw {raised},"
          f" {len(log)} CHGMOD call(s))")

    # ...and the mode DOMAIN reject, the other half of D-SCRERR: 4 is a valid
    # BYTE, so `cp 4` is a test of its own on top of the shared byte coercion,
    # and it must raise ERR 5 (Illegal function call) BEFORE CHGMOD rather than
    # the ERR 2 Syntax error it used to `jp stmt_error` for.
    log = m.record("CHGMOD", regs=("a",))
    raised = []
    m.trap("raise_error", lambda mm: raised.append(mm.cpu.a))
    stream = bytes([s["SCREEN_TOKEN"], 0x11 + 4, 0x00])   # SCREEN 4 (MSX2 only)
    m.poke(BUF, stream)
    m.call("ex_screen", hl=BUF)
    ok = raised == [5] and len(log) == 0
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  SCREEN 4 -> ERR 5 Illegal function call,"
          f" CHGMOD not called  (raise_error saw {raised},"
          f" {len(log)} CHGMOD call(s))")

    # =========================================================================
    # ex_color: COLOR fg,bg,border -> writes FORCLR/BAKCLR/BDRCLR, calls CHGCLR
    # =========================================================================
    # screen.asm writes each colour to its sysvar then calls CHGCLR with A =
    # SCRMOD (the current mode, read from the sysvar).  We preset SCRMOD to a
    # known value, trap CHGCLR, and check the sysvar bytes afterwards.
    # Token stream: [ COLOR_TOKEN | digit_fg | , | digit_bg | , | digit_bd | 0x00 ]
    FG, BG, BD = 7, 1, 1   # typical "white on black" loader setup
    m.mem[s["SCRMOD"]] = 2      # preset a known screen mode so CHGCLR gets A=2

    log_clr = m.record("CHGCLR", regs=("a",))
    stream = (bytes([s["COLOR_TOKEN"], 0x11 + FG,
                     ord(','), 0x11 + BG,
                     ord(','), 0x11 + BD,
                     0x00]))
    m.poke(BUF, stream)
    m.call("ex_color", hl=BUF)

    for svar, want, name in [
        (s["FORCLR"], FG, "FORCLR"),
        (s["BAKCLR"], BG, "BAKCLR"),
        (s["BDRCLR"], BD, "BDRCLR"),
    ]:
        got = m.mem[svar]
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  COLOR {FG},{BG},{BD}"
              f" -> {name}={got:#04x}  (want {want:#04x})")

    # CHGCLR must be called with A = current SCRMOD value (2)
    ok = len(log_clr) == 1 and log_clr[0]["a"] == 2
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  COLOR -> CHGCLR(A=SCRMOD=2)"
          f"  (got A={log_clr[0]['a'] if log_clr else 'never called'})")

    # =========================================================================
    # ex_cls: CLS -> calls CLS BIOS with zero flag set on entry
    # =========================================================================
    # screen.asm: `xor a` sets zero flag, then `call CLS`.  We record the call
    # and assert it was reached.  (We cannot easily inspect the zero flag through
    # the record() API — the trap fires on entry, where the cpu.f Z-bit should
    # still be set from the `xor a`; but asserting the call happened is the
    # primary contract.)
    # Token stream: [ CLS_TOKEN | 0x00 ]
    log_cls = m.record("CLS")
    stream = bytes([s["CLS_TOKEN"], 0x00])
    m.poke(BUF, stream)
    m.call("ex_cls", hl=BUF)
    ok = len(log_cls) == 1
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  CLS -> CLS BIOS called"
          f"  ({len(log_cls)} call(s))")

    # Additionally verify the zero flag was set when CLS was entered
    # (screen.asm: `xor a` -> Z=1; the record log contains a register snapshot
    # taken on entry to the trap — cpu.f Z bit = bit 6).
    if log_cls:
        z_on_entry = bool(log_cls[0]["a"] == 0)   # xor a -> A=0, Z=1
        # We check A=0 as a proxy: `xor a` sets both A=0 and Z=1 atomically,
        # so if A=0 on entry to CLS the handler did what the comment says.
        ok2 = z_on_entry
        fails += not ok2
        print(f"{'PASS' if ok2 else 'FAIL'}  CLS -> A=0 on entry (Z flag set)"
              f"  (A={log_cls[0]['a']:#04x})")
    else:
        fails += 1
        print("FAIL  CLS -> (CLS never reached, can't check A)")

    # =========================================================================
    # ex_key: KEY OFF -> ERAFNK; KEY ON -> DSPFNK
    # =========================================================================
    # screen.asm: compares the token after KEY_TOKEN to OFF_TOKEN/ON_TOKEN.
    # Token streams: [ KEY_TOKEN | OFF_TOKEN | 0x00 ] or [ KEY_TOKEN | ON_TOKEN | 0x00 ]

    # KEY OFF
    log_era = m.record("ERAFNK")
    log_dsp = m.record("DSPFNK")
    stream = bytes([s["KEY_TOKEN"], s["OFF_TOKEN"], 0x00])
    m.poke(BUF, stream)
    m.call("ex_key", hl=BUF)
    ok_off = len(log_era) == 1 and len(log_dsp) == 0
    fails += not ok_off
    print(f"{'PASS' if ok_off else 'FAIL'}  KEY OFF -> ERAFNK called"
          f"  (era={len(log_era)}, dsp={len(log_dsp)})")

    # KEY ON — need a fresh Machine or fresh traps; record() overwrites the trap
    # slot, so calling record() again on a fresh list works.
    log_era2 = m.record("ERAFNK")
    log_dsp2 = m.record("DSPFNK")
    stream = bytes([s["KEY_TOKEN"], s["ON_TOKEN"], 0x00])
    m.poke(BUF, stream)
    m.call("ex_key", hl=BUF)
    ok_on = len(log_dsp2) == 1 and len(log_era2) == 0
    fails += not ok_on
    print(f"{'PASS' if ok_on else 'FAIL'}  KEY ON -> DSPFNK called"
          f"  (era={len(log_era2)}, dsp={len(log_dsp2)})")

    print()
    print("ALL PASS — screen verbs call the correct BIOS entries with correct args"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
