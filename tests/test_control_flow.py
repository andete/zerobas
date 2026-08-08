# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: the BASIC control-flow executor in basic/program.asm, no emulator.

These are the stored-program statements — FOR/NEXT, GOSUB/RETURN, GOTO, IF/THEN,
READ/DATA/RESTORE, ON…GOTO, STOP/CONT, LET — which need the full executor state
(CURLINE, the FOR/GOSUB frame stacks, the DATA cursor). Rather than call each
handler in isolation, we run *small whole programs* through `run_prog` and assert
the observable result in the integer-variable store. That is exactly what the
openMSX differential probes (loops/data/controlflow) verify on real hardware;
this locks the same behaviour in as a fast, emulator-free regression.

Method: tokenise each line body, store it with `store_line` (line-link editor,
already unit-tested), trap BREAKX (never pressed) and CHPUT (discard any
break/error text), then `run_prog` and read variables back via `var_get`.

Oracle: the documented BASIC semantics (FOR sums, GOSUB nesting, RESTORE resets
the DATA cursor, ON N branches to the Nth target) — pure program behaviour, not
the ROM's own output. Single-letter loop/READ variables per the documented
FOR/NEXT divergence (program.asm ex_for comment).
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

ROM = "/tmp/zb_cflow.rom"
SYM = "/tmp/zb_cflow.sym"
SRC = 0xC000          # ASCII line body for tokenise
TOKB = 0xC100         # tokenised body buffer


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def setup(m, lines):
    """Store a program (list of (lineno, ascii-body)) and arm the run traps."""
    m.trap("BREAKX", lambda mm: setattr(mm.cpu, "f", mm.cpu.f & ~0x01))  # CF=0
    m.trap("CHPUT", lambda mm: None)                                     # discard
    m.call("new_prog")
    for lineno, body in lines:
        m.poke(SRC, body.encode("ascii") + b"\x00")
        m.mem[TOKB:TOKB + 192] = b"\x00" * 192
        m.call("tokenise", hl=SRC, de=TOKB)
        m.call("store_line", bc=lineno, hl=TOKB)


def run_program(m, lines):
    setup(m, lines)
    m.call("run_prog")


def var(m, name):
    """Integer variable `name` (single letter) -> its 16-bit value.

    ⚠️ READ THROUGH for_get, NOT var_get_key. var_get_key walks the fixed VARTAB
    pool, which is the LEAN build's int-only store; on the shipped image scalars
    live in the contiguous chain the ARY sub-ROM tenant manages, so var_get_key
    reads back 0 for every variable a program actually set. This test used to run
    on the lean build (msxtest.Machine's rom_base defaulted to $4000) and so never
    noticed. docs/spec-lean-retire-s3-gates.md §5, F-U.

    ⚠️ AND IT TAKES A KEY, NOT A LETTER, SINCE D-FORVAR (spec-basic-forvar.md).
    This was `var_get`, a single-letter shim that upcased its argument and asked
    deftbl_num_type for the letter's default type. The FOR frame now carries the
    loop variable's WHOLE identity, so the caller supplies it in FOR_CUR as
    [name1][name0][type] -- the order `LD (nn),BC` lays BC down in, which is why
    name0 is at +1. The type is still the letter's DEFtbl default, read from
    DEFTBL here rather than hardcoded: that is exactly what the retired lookup
    did, and hardcoding 8 would make this helper lie under DEFINT."""
    s = m.sym
    letter = ord(name.upper())
    m.poke(s["FOR_CUR"], 0)                     # name1: a single-char name
    m.poke(s["FOR_CUR"] + 1, letter)            # name0
    m.poke(s["FOR_CUR"] + 2,
           m.peek(s["DEFTBL"] + letter - ord("A"))[0])
    return m.call("for_get").de


def check(fails, label, got, want):
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {label}: got {got}"
          + ("" if ok else f"  want {want}"))
    return fails + (not ok)


# ---------------------------------------------------------------------------

def test_for_next(m, fails):
    """FOR/NEXT with a named NEXT: sum 1..5."""
    run_program(m, [
        (10, "S=0"),
        (20, "FOR I=1 TO 5"),
        (30, "S=S+I"),
        (40, "NEXT I"),
    ])
    fails = check(fails, "FOR I=1 TO 5 sum", var(m, "S"), 15)   # 1+2+3+4+5
    return fails


def test_for_next_step(m, fails):
    """FOR/NEXT with a negative STEP and a bare NEXT: sum 10,8,6,4,2."""
    run_program(m, [
        (10, "T=0"),
        (20, "FOR J=10 TO 2 STEP -2"),
        (30, "T=T+J"),
        (40, "NEXT"),
    ])
    fails = check(fails, "FOR J=10 TO 2 STEP -2 sum", var(m, "T"), 30)
    return fails


def test_goto_if(m, fails):
    """GOTO back-edge driven by IF <expr> THEN <line>: count to 5."""
    run_program(m, [
        (10, "S=0"),
        (20, "S=S+1"),
        (30, "IF S<5 THEN 20"),
    ])
    fails = check(fails, "IF/THEN/GOTO loop", var(m, "S"), 5)
    return fails


def test_gosub_return(m, fails):
    """GOSUB then RETURN resumes mid-line after the GOSUB statement's line."""
    run_program(m, [
        (10, "A=1"),
        (20, "GOSUB 100"),
        (30, "A=A+1"),
        (40, "END"),
        (100, "A=A*10"),
        (110, "RETURN"),
    ])
    # 1 -> gosub -> *10 = 10 -> return -> +1 = 11
    fails = check(fails, "GOSUB/RETURN", var(m, "A"), 11)
    return fails


def test_read_data_restore(m, fails):
    """READ pulls successive DATA items; RESTORE rewinds the DATA cursor."""
    run_program(m, [
        (10, "READ A"),
        (20, "READ B"),
        (30, "RESTORE"),
        (40, "READ C"),
        (50, "DATA 7,8,9"),
    ])
    fails = check(fails, "READ A (1st DATA)", var(m, "A"), 7)
    fails = check(fails, "READ B (2nd DATA)", var(m, "B"), 8)
    fails = check(fails, "READ C after RESTORE", var(m, "C"), 7)
    return fails


def test_on_goto(m, fails):
    """ON N GOTO branches to the Nth line in the list (N=2 -> 2nd)."""
    run_program(m, [
        (10, "N=2"),
        (20, "ON N GOTO 100,200,300"),
        (30, "R=9"),
        (40, "END"),
        (100, "R=1"),
        (110, "END"),
        (200, "R=2"),
        (210, "END"),
        (300, "R=3"),
        (310, "END"),
    ])
    fails = check(fails, "ON 2 GOTO -> 2nd target", var(m, "R"), 2)
    return fails


def test_stop_cont(m, fails):
    """STOP halts mid-program (CONT resume point recorded); CONT resumes it."""
    setup(m, [
        (10, "A=1"),
        (20, "STOP"),
        (30, "A=2"),
    ])
    m.call("run_prog")
    fails = check(fails, "after STOP (line 30 not run)", var(m, "A"), 1)
    # CONT resumes at the statement after STOP -> runs line 30.
    m.call("ex_cont")
    fails = check(fails, "after CONT (line 30 runs)", var(m, "A"), 2)
    return fails


def test_nested_for(m, fails):
    """Nested FOR/NEXT: outer*inner multiply-accumulate (3x4 = 12 iterations)."""
    run_program(m, [
        (10, "K=0"),
        (20, "FOR I=1 TO 3"),
        (30, "FOR J=1 TO 4"),
        (40, "K=K+1"),
        (50, "NEXT J"),
        (60, "NEXT I"),
    ])
    fails = check(fails, "nested FOR iteration count", var(m, "K"), 12)
    return fails


def run():
    build()
    fails = 0
    groups = [
        ("FOR/NEXT (named)",        test_for_next),
        ("FOR/NEXT (STEP, bare)",   test_for_next_step),
        ("GOTO + IF/THEN",          test_goto_if),
        ("GOSUB/RETURN",            test_gosub_return),
        ("READ/DATA/RESTORE",       test_read_data_restore),
        ("ON…GOTO",                 test_on_goto),
        ("STOP/CONT",               test_stop_cont),
        ("nested FOR/NEXT",         test_nested_for),
    ]
    for title, fn in groups:
        print(f"=== {title} ===")
        fails = fn(Machine(ROM, SYM, rom_base=BASIC_BASE), fails)
        print()

    print("ALL PASS — control-flow executor matches documented BASIC semantics"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
