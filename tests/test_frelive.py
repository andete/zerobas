# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: zerobas-sub2's frelive_tenant (D-FREPLUS14), no emulator.

FRE(n) reads what the VG-8020 reads in every expression shape (Joost,
2026-10-16): the reference counts FRE(0) down to its LIVE stack, so whatever its
evaluator holds open at the FRE costs free memory. main's fre_go
(basic/main.asm) asks sub2/frelive.asm how much: it re-scans the current
statement (SAVTXT) up to the FRE's own `)` (the mark) and returns the statement's
base (18 B in a LET, 14 in a PRINT or an IF condition, 20 in a FOR) plus the
reference's depth there. This test runs the tenant itself over statements
CRUNCHED BY zerobas's own tokeniser and checks the result against the depths
MEASURED on the VG-8020 (scratchpad/freshape_probe.py -> freshape_run3.out; the
44 rows scratchpad/frelive_model.py reproduces), plus the statement bases and
the degrade-to-the-base rows the tenant's header promises.

What it does NOT cover: the main side (fre_go's subtraction and the CALSLT; the
flat harness bridges only zerobas-sub) and the VG-8020 itself -- that is
scratchpad/freshape_probe.py on both machines.
"""

import os
import subprocess
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

BASIC_BASE = 0x2781
MAIN_ROM, MAIN_SYM = tp("zb_frelive_main.rom"), tp("zb_frelive_main.sym")
SUB2_ROM, SUB2_SYM = tp("zb_frelive_sub2.rom"), tp("zb_frelive_sub2.sym")
SRC, DST = 0xC000, 0xC100          # tokeniser in/out (main machine)
STMT = 0xC000                      # the statement (tenant machine)
RESULT = 0xD000                    # the result word

# The VG-8020's depth at the FRE, measured as `B=<shape>` against a plain
# `A=FRE(0)` (freshape_run3.out; variables pre-created, untyped ones double).
MEASURED = {
    "(FRE(0))": 6, "((FRE(0)))": 12, "(((FRE(0))))": 18, "0+FRE(0)": 10, "FRE(0)+0": 0,
    "1*FRE(0)": 10, "FRE(0)*1": 0, "0+1*FRE(0)": 20, "0+0+FRE(0)": 10,
    "0+(0+(0+FRE(0)))": 42, "-(-FRE(0))": 18, "1-(1-FRE(0))": 26, "0 OR FRE(0)": 8,
    "(0=0)*0+FRE(0)": 10, "ABS(FRE(0))": 10, "INT(ABS(FRE(0)))": 20,
    "VAL(STR$(FRE(0)))": 20, "2*FRE(0)/2": 10,
    "I%+FRE(0)-I%": 10, "S!+FRE(0)-S!": 12, "D#+FRE(0)-D#": 16, "E#*FRE(0)": 16,
    "A-K<FRE(0)": 18, "(A-K<FRE(0))=(0=0)": 24, "-1 AND (A-K<FRE(0))": 32,
    "0 XOR (A-K<FRE(0))": 32, "(A-K<FRE(0)) MOD 2": 24, "(A-K<FRE(0))\\1": 24,
    "(A-K<FRE(0))^1": 24, "NOT(A-K<FRE(0))": 30,
    "8 MOD ((A-K<FRE(0))-2)": 38, "8\\((A-K<FRE(0))-2)": 38, "2^(A-K<FRE(0))": 34,
    "1/((A-K<FRE(0))-2)": 40, "0 EQV (A-K<FRE(0))": 32, "-1 IMP (A-K<FRE(0))": 32,
    "0=(A-K<FRE(0))": 36, "0<>(A-K<FRE(0))": 36, "-1>=(A-K<FRE(0))": 36,
    "0<=(A-K<FRE(0))": 36, "0>(A-K<FRE(0))": 36, "R((A-K<FRE(0))+1)": 42,
    "A%-K%<FRE(0)": 12, "VAL(\"\"+STR$(FRE(0)))": 22,
}

# (statement, which FRE (0-based), expected tenant result, why)
STATEMENTS = [
    # the statement bases (freshape_run3.out's P rows)
    ("A=FRE(0)", 0, 18, "LET: the base row"),
    ("LET A=FRE(0)", 0, 18, "LET keyword"),
    ('PRINT"[print";FRE(0);"]"', 0, 14, "print: 4 B above a LET"),
    ('PRINT"[print2";0;FRE(0);"]"', 0, 14, "print2: `;` starts a fresh item"),
    ('?FRE(0)', 0, 14, "`?` is PRINT"),
    ("R(0)=FRE(0)", 0, 18, "arytgt: the subscripted target is skipped"),
    ("FOR I=FRE(0) TO 99999!", 0, 20, "forstart: 2 B below a LET"),
    ("B$=STR$(FRE(0))", 0, 28, "letstr: STR$ 10"),
    ("IF (A-K<FRE(0)) THEN B=1", 0, 14 + 24, "ifcond: PRINT's base + ( 6 + < 18"),
    # the width comes from DEFTBL for an untyped name (I is DEFINT here)
    ("B=I+FRE(0)", 0, 18 + 10, "DEFINT I: an integer left operand"),
    # two FREs: the mark picks THIS one
    ("B=FRE(0)+FRE(0)", 0, 18, "first FRE: nothing pending"),
    ("B=FRE(0)+FRE(0)", 1, 18 + 12, "second FRE: + pending over FRE's single"),
    # binfre's depth battery (docs/binfre-vg8020-characterization.md §3.1, the
    # VG-8020): FRE(0)-FRE(0) 12 -- FRE's result is a SINGLE (8 + 4) -- and 6 more
    # per parenthesis around the second
    ("PRINT FRE(0)-FRE(0)", 1, 14 + 12, "dep-same-num: 12"),
    ("PRINT FRE(0)-(FRE(0))", 1, 14 + 18, "dep-paren: 18"),
    ("PRINT FRE(0)-((FRE(0)))", 1, 14 + 24, "dep-paren2: 24"),
    ("PRINT FRE(0)-FRE(0)", 0, 14, "the first FRE: nothing pending"),
    ("B=FRE(FRE(0))", 1, 18 + 10, "inner FRE: the outer one is a function"),
    ("B=FRE(FRE(0))", 0, 18, "outer FRE: nothing pending"),
    # separators restart the expression
    ("FOR I=1 TO FRE(0)", 0, 20, "after TO: nothing pending (unmeasured)"),
    ("ON FRE(0) GOTO 10,20", 0, 18, "another statement: LET's base"),
    ("PRINT USING \"###\";FRE(0)", 0, 14, "PRINT USING: `;` restarts"),
    ("PRINT #1,FRE(0)", 0, 14, "PRINT #: `#` skipped, `,` restarts (unmeasured)"),
    # degrade to the base alone, never a hang or a read past the statement
    ('PRINT "A"(FRE(0))', 0, 14, "juxtaposed operand: bail to the base"),
    ("B=FRE(0)", 0, 18, "(control for the DEF FN row below)"),
]


def toks_skip(t, i):
    """Index past the token at t[i] (payload-aware, the tenant's fl_tok rule)."""
    b = t[i]
    if b == 0x22:
        j = i + 1
        while t[j] not in (0x22, 0):
            j += 1
        return j + 1 if t[j] == 0x22 else j
    n = {0x0F: 1, 0xFF: 1, 0x1C: 2, 0x1D: 4, 0x1F: 8}.get(b, 2 if 0x0B <= b <= 0x0E else 0)
    return i + 1 + n


def mark_of(t, nth):
    """One past the `)` closing the nth FRE( in token stream t."""
    i, seen = 0, 0
    while t[i] != 0:
        if t[i] == 0xFF and t[i + 1] == 0x8F:
            if seen == nth:
                j = i + 2
                while t[j] == 0x20:
                    j += 1
                assert t[j] == 0x28, "FRE without ("
                depth, j = 1, j + 1
                while depth:
                    if t[j] == 0x28:
                        depth += 1
                    elif t[j] == 0x29:
                        depth -= 1
                    j = toks_skip(t, j)
                return j
            seen += 1
        i = toks_skip(t, i)
    raise AssertionError("no such FRE")


def build():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"), MAIN_ROM, MAIN_SYM],
                   check=True, capture_output=True, cwd=ROOT)
    subprocess.run(["pasmo", "-I", "sub", "--bin", "sub2/sub2.asm", SUB2_ROM, SUB2_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def run():
    build()
    main = Machine(MAIN_ROM, MAIN_SYM, rom_base=BASIC_BASE)
    sub2 = Machine(SUB2_ROM, SUB2_SYM, rom_base=0x0000)
    s = sub2.sym
    fails = 0

    def crunch(text):
        main.poke(SRC, text.encode("ascii") + b"\x00")
        main.mem[DST:DST + 256] = b"\x00" * 256
        main.call("tokenise", hl=SRC, de=DST)
        return bytes(main.mem[DST:DST + 256])

    def tenant(text, nth=0, mark=None, deftbl=None):
        t = crunch(text)
        m = sub2
        m.mem[STMT:STMT + 256] = t
        dt = bytearray([8] * 26)                     # boot: every letter double
        for letter, w in (deftbl or {}).items():
            dt[ord(letter) - ord("A")] = w
        m.poke(s["DEFTBL"], bytes(dt))
        m.poke_w(s["SAVTXT"], STMT)
        m.poke_w(s["CTLLIM"], 0x8000)                # far below the stack
        m.poke_w(RESULT, 0xA5A5)
        mk = STMT + mark_of(t, nth) if mark is None else mark
        cpu = m.call("frelive_tenant", hl=RESULT, de=mk)
        assert cpu.sp == 0xF380, f"stack not balanced: SP={cpu.sp:#06x}"
        return m.mem[RESULT] | m.mem[RESULT + 1] << 8

    def report(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:44} -> {got}" + ("" if ok else f"   want {want}"))

    for expr, depth in MEASURED.items():
        report(f"B={expr}", tenant("B=" + expr), 18 + depth)

    for text, nth, want, why in STATEMENTS:
        dt = {"I": 2} if "DEFINT" in why else None
        report(f"{text}  [{why}]"[:60], tenant(text, nth, deftbl=dt), want)

    # several statements on one line: SAVTXT is the CURRENT one's start
    t = crunch("A=1:PRINT 0+FRE(0)")
    colon = t.index(0x3A)
    sub2.mem[STMT:STMT + 256] = t
    sub2.poke_w(s["SAVTXT"], STMT + colon + 1)
    sub2.poke_w(RESULT, 0)
    sub2.call("frelive_tenant", hl=RESULT, de=STMT + mark_of(t, 0))
    report("A=1:PRINT 0+FRE(0) (SAVTXT past the `:`)",
           sub2.mem[RESULT] | sub2.mem[RESULT + 1] << 8, 14 + 10)

    # a FRE in a DEF FN body: the mark is not in the calling statement -> base
    report("mark before the statement (DEF FN body)", tenant("B=FNF(0)", mark=STMT - 40), 18)
    report("mark past the statement (DEF FN body)", tenant("B=FNF(0)", mark=STMT + 200), 18)
    # the pool's floor: a near-full machine bails before it stacks anything
    t = crunch("B=(((FRE(0))))")
    sub2.mem[STMT:STMT + 256] = t
    sub2.poke_w(s["SAVTXT"], STMT)
    sub2.poke_w(s["CTLLIM"], 0xF380 - 40)
    sub2.poke_w(RESULT, 0)
    sub2.call("frelive_tenant", hl=RESULT, de=STMT + mark_of(t, 0))
    report("CTLLIM within the margin: base alone", sub2.mem[RESULT] | sub2.mem[RESULT + 1] << 8, 18)

    print("\n" + (f"{fails} FAILED" if fails else
                  "ALL PASS -- frelive_tenant reproduces the VG-8020's measured FRE depths"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
