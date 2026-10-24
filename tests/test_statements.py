# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: assorted statement front-ends run through the executor, no emulator.

Covers the statement handlers reached via the dispatcher that the other tests
bypass by calling internals directly:
  - PRINT  (ex_print + exp_* + print_number) — captured CHPUT stream
  - GOTO   (ex_goto, the bare statement form)
  - CLEAR  (ex_clear / clr_himem — records HIMEM)
  - WIDTH  (ex_width -> zerobas-sub2's scr_width since D-P0CB slice D —
             sets LINLEN, re-inits via CHGMOD)

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
BASIC_BASE = 0x2781

ROM = tp("zb_stmt.rom")
SYM = tp("zb_stmt.sym")
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
    # 🔴 D-SPMERGE step 4: `rp_lp` re-bases the machine stack on the pool
    # frontier (`ld sp,(CSP)`) on every pass -- that is what makes the pool's
    # free sites symmetric. On a real machine `ctl_reset` publishes `CSP` at
    # cold boot before anything runs (MEASURED 2026-09-12: ctl_reset at t=2.641
    # and t=2.656, first `repl` at t=2.713 with CSP=D906 already), but it
    # derives the value through a SUB-ROM call this harness does not have, so
    # here it only gets as far as its own `CSP := 0` -- and `ld sp,(CSP)` then
    # takes SP to 0 and the CPU runs away. Standing in for the boot is the same
    # fix D-TXTCEIL made for `SL_CEIL`: supply what the machine publishes. The
    # value only has to sit in the harness's stack band [0x8000,0xf380] AND
    # below every private cell: $F000 sat in a 174-byte hole until D-WSZERO slice
    # 5 packed the workspace (2026-10-14) and the pool then grew over live cells.
    # TXTMAX_NODISK is the diskless program-RAM top, under every private cell.
    m.trap("ctl_reset", lambda mm: (mm.poke_w(mm.sym["CSP"], mm.sym["TXTMAX_NODISK"]),
                                       mm.poke_w(mm.sym["CTLLIM"], 0x8000)))
    out = m.capture_chput()
    m.call("new_prog")
    for lineno, body in lines:
        m.poke(SRC, body.encode("ascii") + b"\x00")
        m.mem[TOKB:TOKB + 192] = b"\x00" * 192
        m.call("tokenise", hl=SRC, de=TOKB)
    # 🔴 D-TXTCEIL: `store_line` now bounds the store against `SL_CEIL`, a RAM
    # cell that `dl_store` publishes on the real machine (from fch_ctx_addr(1) =
    # strheap_varceil). These tests call `store_line` DIRECTLY, so they must
    # supply it too -- without it the cell is 0 in this harness's zeroed RAM,
    # every store is refused as OOM, and the abort funnel does `ld sp,(SAVSTK)`
    # with SAVSTK=0 and runs away (msxtest.StackLost). The value is TXTMAX, which
    # is exactly the CONSTANT the code compared against before, so these rows go
    # on testing what they tested.
        m.poke_w(m.sym["SL_CEIL"], m.sym["TXTMAX"])
        m.call("store_line", bc=lineno, hl=TOKB)
    m.call("run_prog")
    return bytes(out)


def var(m, name):
    # ⚠️ for_get, NOT var_get_key: var_get_key walks the fixed VARTAB pool, the
    # LEAN build's int-only store. On the shipped image scalars live in the
    # contiguous chain the ARY sub-ROM tenant manages, so var_get_key reads back 0
    # for everything a program set. This test ran on the lean build until S3
    # (docs/spec-lean-retire-s3-gates.md §5, F-U) and so never noticed.
    # ⚠️ AND IT TAKES A KEY, NOT A LETTER, SINCE D-FORVAR: the FOR frame carries
    # the loop variable's whole identity as [name1][name0][type] (the order
    # `LD (nn),BC` lays BC down in, so name0 is at +1). Type from DEFTBL, not
    # hardcoded -- the retired shim looked it up, and a hardcoded 8 would lie
    # under DEFINT. docs/spec-basic-forvar.md §4.5.
    s = m.sym
    letter = ord(name.upper())
    m.poke(s["FOR_CUR"], 0)                     # name1: a single-char name
    m.poke(s["FOR_CUR"] + 1, letter)            # name0
    m.poke(s["FOR_CUR"] + 2,
           m.peek(s["DEFTBL"] + letter - ord("A"))[0])
    return m.call("for_get").de


def run():
    build()
    fails = 0

    def check(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}: got {got!r}"
              + ("" if ok else f"  want {want!r}"))

    # --- NEW as a STATEMENT (D-NEWSTMT, 2026-09-12) --------------------------
    # 🔴 THE REGRESSION GATE FOR A DEFECT THE DRAIN FOUND. `stmt_table` had RUN and
    # CLEAR but no NEW_TOKEN, so a PROGRAM reaching `NEW` fell through to a Syntax
    # error while the reference ran it: MEASURED on the VG-8020, `10 PRINT"[A]":NEW`
    # prints `[A]` then `Ok`, and a following `20 LIST` prints NOTHING -- so NEW
    # erases the program AND stops. This row pins the printing half, which is the
    # half that was silently wrong: before the fix the capture stopped at the error.
    # ⚠️ It does NOT pin the erase -- this harness runs `run_prog` over a program it
    # poked in itself, so "the text area is empty afterwards" is a different
    # assertion and belongs with the machine-level rows, not here.
    check('PRINT then NEW', run_prog_cap(Machine(ROM, SYM, rom_base=BASIC_BASE),
                                         [(10, 'PRINT "A":NEW')]),
          b"A\r\n")

    # --- PRINT (ex_print): documented MSX integer format + separators --------
    # Non-negative number: leading space (sign slot) + digits + trailing space.
    check("PRINT 42", run_prog_cap(Machine(ROM, SYM, rom_base=BASIC_BASE), [(10, "PRINT 42")]),
          b" 42 \r\n")
    # String literal printed verbatim, then CR/LF.
    check('PRINT "HI"', run_prog_cap(Machine(ROM, SYM, rom_base=BASIC_BASE), [(10, 'PRINT "HI"')]),
          b"HI\r\n")
    # ';' joins with no extra spacing (each number keeps its own framing).
    # Regression for the print_number HL-clobber bug: items after the first
    # numeric one must still print (exp_num now guards the token cursor).
    check("PRINT 1;2", run_prog_cap(Machine(ROM, SYM, rom_base=BASIC_BASE), [(10, "PRINT 1;2")]),
          b" 1  2 \r\n")
    check("PRINT 1;2;3", run_prog_cap(Machine(ROM, SYM, rom_base=BASIC_BASE), [(10, "PRINT 1;2;3")]),
          b" 1  2  3 \r\n")
    # number followed by a string literal (cursor survives the number -> string).
    check('PRINT 7;"HI"', run_prog_cap(Machine(ROM, SYM, rom_base=BASIC_BASE), [(10, 'PRINT 7;"HI"')]),
          b" 7 HI\r\n")
    # Trailing ';' suppresses the closing newline.
    check('PRINT "X";', run_prog_cap(Machine(ROM, SYM, rom_base=BASIC_BASE), [(10, 'PRINT "X";')]),
          b"X")
    # Bare PRINT prints an empty line.
    check("PRINT (bare)", run_prog_cap(Machine(ROM, SYM, rom_base=BASIC_BASE), [(10, "PRINT")]),
          b"\r\n")

    # --- GOTO (ex_goto, bare statement form) ---------------------------------
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    run_prog_cap(m, [(10, "GOTO 30"), (20, "A=1"), (30, "A=2")])
    check("GOTO skips line 20 (A)", var(m, "A"), 2)

    # --- CLEAR <n>,<himem> (ex_clear / clr_himem records HIMEM) --------------
    # 🔴 THIS CHECK USED TO TYPE `CLEAR ,&HABCD` AND IT ASSERTED A FORM THE
    # LANGUAGE DOES NOT HAVE (D-CLRFIX 2026-08-23,
    # docs/spec-basic-clrfix.md). `CLEAR ,himem` -- string space omitted -- is a
    # **Syntax error on the VG-8020 AND the CF-3300**, so the assertion was
    # pinning own-design behaviour against nothing. zerobas stopped accepting it
    # when ex_clear's `cp ',' / jr z,clr_himem` was deleted (-4 B) and this test
    # went red, which is the gate doing its job.
    # The QUESTION it was written for -- does CLEAR's second argument reach
    # HIMEM? -- is unchanged and is now asked with the legal two-argument form.
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    run_prog_cap(m, [(10, "CLEAR 200,&HABCD")])
    himem = m.mem[m.sym["HIMEM"]] | (m.mem[m.sym["HIMEM"] + 1] << 8)
    check("CLEAR 200,&HABCD sets HIMEM", himem, 0xABCD)

    # ...and the refusal itself is now pinned, so deleting the guard cannot go
    # unnoticed the way accepting the form did. HIMEM must be UNTOUCHED.
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    m.mem[m.sym["HIMEM"]] = 0x34
    m.mem[m.sym["HIMEM"] + 1] = 0x12
    run_prog_cap(m, [(10, "CLEAR ,&HABCD")])
    himem = m.mem[m.sym["HIMEM"]] | (m.mem[m.sym["HIMEM"] + 1] << 8)
    check("CLEAR ,&HABCD leaves HIMEM alone (Syntax error)", himem, 0x1234)

    # --- WIDTH n (ex_width sets LINLEN) --------------------------------------
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    m.mem[m.sym["SUBSLOT2"]] = 0x8F        # D-P0CB slice D: WIDTH runs in sub2
                                            # (3-3); the harness bridges it once
                                            # SUBSLOT2 says the ROM is there
    run_prog_cap(m, [(10, "WIDTH 32")])
    check("WIDTH 32 sets LINLEN", m.mem[m.sym["LINLEN"]], 32)

    # --- LET / FOR create their SCALAR target BEFORE the right side ----------
    # 🧮 D-LETNEWFIRST (2026-10-19). Measured on the VG-8020
    # (scratchpad/letnew_probe.py -> scratchpad/letnew_run.out): FRE(0) inside
    # `X=...FRE(0)...` with X new reads the new entry already spent -- 11 B for a
    # double, 5 int, 7 single, 6 for a string's entry, 11 for `FOR I=FRE(0)`, 0 on
    # every `.pre` twin. These machines leave SUBSLOT2 at 0, so msxtest's sub2
    # bridge reports sub2 ABSENT and FRE(0)'s live-stack tenant never runs, so
    # the witness is VARPTR, which FINDS and never creates (D-VPTRDOM): VARPTR(X)
    # inside X's own right side is Illegal function call unless X already exists.
    # Before this slice every row below printed `Illegal function call in 10`.
    def run1(lines):
        m1 = Machine(ROM, SYM, rom_base=BASIC_BASE)
        m1.poke_w(m1.sym["POOLSIZE"], 200)    # the cold-boot string space (init)
        return run_prog_cap(m1, lines)

    check("LET X (double) exists before its RHS",
          run1([(10, "X=VARPTR(X):PRINT X=VARPTR(X)")]), b"-1 \r\n")
    check("LET X% exists before its RHS",
          run1([(10, "X%=VARPTR(X%):PRINT X%=VARPTR(X%)")]), b"-1 \r\n")
    check("LET X! exists before its RHS",
          run1([(10, "X!=VARPTR(X!):PRINT X!=VARPTR(X!)")]), b"-1 \r\n")
    check("the LET keyword, X#",
          run1([(10, "LET X#=VARPTR(X#):PRINT X#=VARPTR(X#)")]), b"-1 \r\n")
    check("LET A$ exists (empty) before its RHS",
          run1([(10, 'A$=STR$(VARPTR(A$))+MID$(A$,1):PRINT VAL(A$)=VARPTR(A$)')]),
          b"-1 \r\n")
    # Both arms of the string store, on a new and on an existing target: a
    # program literal by REFERENCE (D-LITREF), a computed RHS by COPY.
    check("string LET: by reference and by copy, new and existing",
          run1([(10, 'A$="AB":A$=A$+"C":B$="Q":B$=B$+B$:PRINT A$;B$;LEN(A$)')]),
          b"ABCQQ 3 \r\n")
    check("FOR I exists before its start expression",
          run1([(10, "FOR I=0*VARPTR(I) TO 0:NEXT:PRINT I")]), b" 1 \r\n")
    check("FOR I% exists before its start expression",
          run1([(10, "FOR I%=0*VARPTR(I%) TO 0:NEXT:PRINT I%")]), b" 1 \r\n")

    # The consequence the reference's order implies (inferred, not a measured row):
    # an error RAISED by the right side leaves the target created, at zero.
    check("an erroring RHS leaves the new target standing at 0",
          run1([(10, "ON ERROR GOTO 30"), (20, "Z=1/0"),
                (30, "PRINT Z;VARPTR(Z)<>0:END")]),
          b" 0 -1 \r\n")

    # An EXISTING target is untouched by the move: same entry, same address, the
    # store lands in it, and the chain holds exactly one entry per name in
    # creation order (X then P, 11 B each), never a second X.
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    out = run_prog_cap(m, [(10, "X=5:P=VARPTR(X):X=X+1:X%=2:X%=X%*3"),
                           (20, "PRINT X;VARPTR(X)=P;X%")])
    check("existing targets: value, address, int", out, b" 6 -1  6 \r\n")
    base = m.mem[m.sym["PRGEND"]] | (m.mem[m.sym["PRGEND"] + 1] << 8)
    base += 2
    end = m.mem[m.sym["ARYTAB"]] | (m.mem[m.sym["ARYTAB"] + 1] << 8)
    chain, a = [], base
    while a < end:
        t = m.mem[a + 2]
        chain.append((chr(m.mem[a]) + (chr(m.mem[a + 1]) if m.mem[a + 1] else ""), t))
        a += 3 + (3 if t == 1 else t)
    check("existing targets: the chain is X, P, X% -- one entry each",
          chain, [("X", 8), ("P", 8), ("X", 2)])

    print()
    print("ALL PASS — PRINT/GOTO/CLEAR/WIDTH match documented statement behaviour"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
