# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: D-EVALSLOPE (2026-10-20) -- the evaluator's ONE precedence climber
(basic/expr.asm, `ev_logic` / `ev_e` / `ev_pw` and the cl_* loop), on the host Z80.

The three precedence layers (ev_logic -> ev_not -> ev_rel -> ev_e -> ev_f) became
one loop with an operator stack on the machine stack (docs/spec-basic-deepexpr-
guard.md §5.3). This file pins what that must and must not change:

  E1  precedence and associativity at every level boundary, each row chosen so
      that the WRONG grouping gives a DIFFERENT value (a row that agrees under
      both groupings proves nothing -- XOR/EQV and IMP/OR are unobservable
      against each other and have no row here);
  E2  every construct nested deep (each level PENDING while the next is parsed)
      still evaluates right -- the frames come back off the stack in order;
  E3  the stack each pending construct holds, as built: `(` 6 B, `1+(` 12,
      `1 AND (` 10, `1<(` 12, `-(` 12, `NOT` 2, `NOT(` 8, `ABS(` 12 (the
      VG-8020's, spec-basic-frelive.md: 6, 16, 14, 18, 12, 6, 12, 16) -- and,
      since the typed-frame step (push_lhs_frame sizes the pending lhs by its
      type), `1.5+(` 14 and `1#+(` 18 (the VG-8020's 8 + width + `(`: 18, 22);
  E2f the typed frame at depth: every typed operator (+ - * / and the
      relationals) nested with an int, a single, a double and a MIXED lhs
      (int16 lhs over a double rhs and back, int overflow promoting at depth),
      each value exact in BCD, read back from FAC whole;
  E4  the NOT prefix's own stack test (cl_not) refuses exactly where stk_guard
      would at the same SP, and a NOT chain at the edge defers ERR 7 without the
      stack ever reaching CTLLIM;
  E5  near the edge every nested shape either completes with the right value or
      defers ERR 7 -- and never takes the stack to or below CTLLIM.

Oracle basis: E1/E2's values are the language's (MSX-BASIC precedence, 16-bit
two's-complement integers, MOD signed like the dividend, \\ truncating) -- the
same answers the old layers gave (scratchpad/evalslope_probe.py diffs 132
outcome rows between the builds, all identical). E3's numbers are this build's
own measurement, pinned so a frame that grows is seen; E4/E5 check zerobas's
own safety property, which no reference reading can show.
"""

import os
import subprocess
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402
from decimal import Decimal as D  # noqa: E402

ROM = tp("zb_evalslope.rom")
SYM = tp("zb_evalslope.sym")
RELOC_BASE = 0x2781
SRC, TOKBUF = 0xC000, 0xC100
SP_ENTRY = 0xF37E          # eval's entry SP: Machine.call's $F380 less its sentinel


def build():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"), ROM, SYM],
                   check=True, capture_output=True)


def w16(v):
    return v & 0xFFFF


def mmod(a, b):            # MSX MOD: the sign of the dividend
    r = abs(a) % abs(b)
    return -r if a < 0 else r


def mdiv(a, b):            # MSX \: truncate toward zero
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def mod_nest(n):
    """n pending MODs and never a 0 divisor: 200MOD(201MOD(...(300)))."""
    return "".join(f"{200 + i}MOD(" for i in range(n)) + "300" + ")" * n


def run():
    build()
    m = Machine(ROM, SYM, rom_base=RELOC_BASE)
    s = m.sym
    m.poke_w(s["PRGEND"], 0x9000)
    m.poke(0x9000, b"\x00\x00")
    m.poke_w(s["ARYTAB"], 0x9002)
    m.poke(0x9002, b"\x00\x00")
    m.poke_w(s["POOLSIZE"], 4096)
    m.call("heap_reset")
    R = s["STK_EVAL_RESERVE"]
    CTLLIM, FPERR, OOM = s["CTLLIM"], s["FPERR"], s["FPERR_OOM"]
    LOOSE = 0x9100
    # E4/E5 sweep CTLLIM up to here and no closer. Above it CTLLIM sits inside
    # the frames eval itself pushes before ANY guard has run (its cursor save,
    # the sentinel, the first operand's string probe): the old layers reached
    # CTLLIM from SP_ENTRY-38 on (`-(`), the climber from SP_ENTRY-28 --
    # statement-level stack, which DIM's 256 B reserve keeps clear, not the
    # evaluator's (scratchpad/evalslope_probe.py's notes).
    EDGE_TOP = SP_ENTRY - 40
    fails = 0

    lo = [0x10000]
    hits = {}
    step = m.cpu.step

    def tracked():
        pc = m.cpu.pc
        if pc in hits:
            hits[pc].append(m.cpu.sp)
        step()
        if m.cpu.sp < lo[0]:
            lo[0] = m.cpu.sp
    m.cpu.step = tracked

    def check(label, ok, detail=""):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail and not ok else ""))

    def fac_value():
        """FAC/FACTYP -> exact Decimal (tests/test_float.py's decode_fac)."""
        fac = s["FAC"]
        lead = m.peek(fac)[0]
        if lead == 0:
            return D(0)
        n = 7 if m.peek(s["FACTYP"])[0] == 8 else 3
        digits = "".join(f"{b >> 4}{b & 15}" for b in m.peek(fac + 1, n))
        sign = -1 if lead & 0x80 else 1
        return sign * D(int(digits)) * (D(10) ** ((lead & 0x7F) - 64 - len(digits)))

    def ev(text, ctllim=LOOSE):
        m.poke(SRC, text.encode("ascii") + b"\x00")
        m.mem[TOKBUF:TOKBUF + 256] = b"\x00" * 256
        m.call("tokenise", hl=SRC, de=TOKBUF)
        m.poke(FPERR, 0)
        m.poke(s["ERRMARK"], 0)
        m.poke_w(s["TEMPPT"], s["TEMPPOOL"])
        m.poke_w(CTLLIM, ctllim)
        lo[0] = 0x10000
        cpu = m.call("eval", hl=TOKBUF)
        return cpu.de & 0xFFFF, m.mem[FPERR], lo[0], cpu.hl - TOKBUF

    # ------------------------------------------------------------------
    print("# --- E1 precedence / associativity, each row discriminating ---")
    E1 = [
        ("1+2*3", 7), ("2*3+1", 7), ("10-4-3", 3), ("64\\4\\2", 8),
        ("100MOD7MOD3", 2), ("9MOD5\\2", 1), ("9\\2MOD3", 1), ("2+7MOD4", 5),
        ("2*7MOD4", 2), ("7MOD4*2", 7), ("7\\2*2", 1), ("2*7\\4", 3),
        ("-1+2", 1), ("2*-3", -6), ("--2", 2),
        ("1<2<3", -1), ("3>2>1", 0), ("1=1=1", 0), ("1+1=2", -1), ("2=1+1", -1),
        ("1<>2", -1), ("2<=1", 0), ("2>=2", -1), ("2=<2", -1),
        ("6AND3OR8", 10), ("8OR6AND3", 10), ("6XOR3AND1", 7), ("1OR2XOR3", 0),
        ("6IMP1AND3", -7), ("1<2AND3<4", -1), ("1<2OR3<4AND0", -1),
        ("NOT1=2", -1), ("NOT1AND0", 0), ("NOT0OR1", -1), ("1ANDNOT0", 1),
        ("NOT1+1", -3), ("NOTNOT5", 5), ("NOT(1)+1", -3),
        ("(1+2)*3", 9), (" ( 1 + 2 ) * 3 ", 9),
    ]
    for text, want in E1:
        de, fe, _, _ = ev(text)
        check(f"{text} = {want}", de == w16(want) and fe == 0, f"DE={de:04X} FPERR={fe}")

    # ------------------------------------------------------------------
    print("# --- E2 deep nesting: every level pending, then unwound in order ---")

    def nest(n, op, lhs, inner):
        return (f"{lhs}{op}(" * n) + str(inner) + ")" * n

    def fold(n, f, inner):
        v = inner
        for _ in range(n):
            v = f(v)
        return v

    E2 = [
        ("(" * 40 + "1" + ")" * 40, 1),
        (nest(30, "+", 1, 1), 31),
        (nest(25, "-", 10, 1), fold(25, lambda v: 10 - v, 1)),
        (nest(10, "*", 2, 1), 1024),
        (nest(20, "\\", 1000, 999), fold(20, lambda v: mdiv(1000, v), 999)),
        (nest(25, "AND", 7, 5), 5),
        (nest(25, "XOR", 6, 1), fold(25, lambda v: 6 ^ v, 1)),
        (nest(25, "OR", 0, 9), 9),
        (nest(20, "<", 0, 1), fold(20, lambda v: -1 if 0 < v else 0, 1)),
        (nest(20, "=", 0, 0), fold(20, lambda v: -1 if 0 == v else 0, 0)),
        ("-(" * 21 + "1" + ")" * 21, -1),
        ("NOT(" * 21 + "0" + ")" * 21, -1),
        ("NOT" * 41 + "0", -1),
        ("ABS(" * 20 + "-5" + ")" * 20, 5),
    ]
    for text, want in E2:
        de, fe, _, _ = ev(text)
        check(f"{text[:28]}{'...' if len(text) > 28 else ''} = {want}",
              de == w16(want) and fe == 0, f"DE={de:04X} FPERR={fe}")
    # MOD nested with no zero divisor anywhere: 200MOD(201MOD(...(300)))
    text = mod_nest(10)
    de, fe, _, _ = ev(text)
    want = 300
    for i in reversed(range(10)):
        want = mmod(200 + i, want)
    check(f"200MOD(201MOD(...209MOD(300))) = {want}", de == w16(want) and fe == 0,
          f"DE={de:04X}")

    # ------------------------------------------------------------------
    print("# --- E2f the typed frame at depth: int / single / double / mixed lhs ---")
    FT = s["FACTYP"]

    def nestx(n, op, lhs, inner):
        return (f"{lhs}{op}(" * n) + inner + ")" * n

    def foldd(n, f, inner):
        v = D(inner)
        for _ in range(n):
            v = f(v)
        return v

    rel = lambda c: D(-1) if c else D(0)  # noqa: E731
    E2F = [
        # (text, expected exact value) -- every operand and partial result exact
        # in 14 BCD digits, so no rounding question can hide in the comparison
        (nestx(20, "+", "1.5", "2.5"), D("32.5")),
        (nestx(21, "-", "1.5", ".5"), foldd(21, lambda v: D("1.5") - v, ".5")),
        (nestx(10, "*", "1.5", "1"), D("1.5") ** 10),
        (nestx(11, "/", "1.5", "2"), foldd(11, lambda v: D("1.5") / v, "2")),
        (nestx(20, "<", ".5", "1"), foldd(20, lambda v: rel(D(".5") < v), "1")),
        (nestx(20, "=", "0!", "0"), foldd(20, lambda v: rel(v == 0), "0")),
        (nestx(20, "+", "1.25#", "1"), D("26")),
        (nestx(21, "-", "2.5#", "1#"), foldd(21, lambda v: D("2.5") - v, "1")),
        (nestx(10, "*", "1.5#", "1#"), D("1.5") ** 10),
        (nestx(11, "/", "3#", "4#"), foldd(11, lambda v: D(3) / v, "4")),
        (nestx(20, ">", "0#", "1#"), foldd(20, lambda v: rel(D(0) > v), "1")),
        (nestx(20, "<>", ".5#", "1"), foldd(20, lambda v: rel(D(".5") != v), "1")),
        # mixed: an int16 lhs over a double rhs (promotion at every level) ...
        (nestx(30, "+", "1", "1#"), D(31)),
        (nestx(20, "*", "2", ".5#"), D(2) ** 20 * D(".5")),
        (nestx(20, "-", "1", "2.5"), foldd(20, lambda v: 1 - v, "2.5")),
        # ... a double / single lhs over an int16 rhs ...
        (nestx(30, "+", "1#", "1"), D(31)),
        (nestx(20, "*", ".5", "1024"), D(".5") ** 20 * 1024),
        # ... int16 overflow promoting to double at depth, and alternating types
        (nestx(20, "+", "32767", "1"), D(32767 * 20 + 1)),
        ("1+(1#+(1.5+(2+(2.5#+(3+(3.5+(4#+(4.5+(5)))))))))", D("28")),
        ("1#*(2*(1.5*(2#*(.5*(4*(1.25#*(8)))))))", D(120)),
        ("1<(1#+(1.5<(2#=(1+(1)))))", D(0)),
    ]
    for text, want in E2F:
        de, fe, _, _ = ev(text)
        got = D(w16(de) - (0x10000 if de & 0x8000 else 0)) if m.peek(FT)[0] == 2 else fac_value()
        check(f"{text[:34]}{'...' if len(text) > 34 else ''} = {want}",
              got == want and fe == 0, f"got={got} FACTYP={m.peek(FT)[0]} FPERR={fe}")

    # ------------------------------------------------------------------
    print("# --- E3 the stack per pending construct, as built ---")
    SHAPES = [
        ("(",       lambda n: "(" * n + "1" + ")" * n,                 6),
        ("1+(",     lambda n: "1+(" * n + "1" + ")" * n,              12),
        ("1*(",     lambda n: "1*(" * n + "1" + ")" * n,              12),
        ("1.5+(",   lambda n: "1.5+(" * n + "1" + ")" * n,            14),
        ("1#+(",    lambda n: "1#+(" * n + "1" + ")" * n,             18),
        ("1.5*(",   lambda n: "1.5*(" * n + "1" + ")" * n,            14),
        ("1#/(",    lambda n: "1#/(" * n + "1" + ")" * n,             18),
        ("1AND(",   lambda n: "1AND(" * n + "1" + ")" * n,            10),
        ("1MOD(",   mod_nest,                                         10),
        ("1<(",     lambda n: "1<(" * n + "1" + ")" * n,              12),
        ("1.5<(",   lambda n: "1.5<(" * n + "1" + ")" * n,            14),
        ("1#<(",    lambda n: "1#<(" * n + "1" + ")" * n,             18),
        ("-(",      lambda n: "-(" * n + "1" + ")" * n,               12),
        ("NOT",     lambda n: "NOT" * n + "0",                         2),
        ("NOT(",    lambda n: "NOT(" * n + "0" + ")" * n,              8),
        ("ABS(",    lambda n: "ABS(" * n + "1" + ")" * n,             12),
    ]
    for name, mk, want in SHAPES:
        depths = [SP_ENTRY - ev(mk(n))[2] for n in (6, 7, 8)]
        sl = {depths[1] - depths[0], depths[2] - depths[1]}
        check(f"{name:6s} holds {want} B per pending level", sl == {want}, f"slopes={sl}")
    _, _, low, _ = ev("1")
    check("a plain factor reaches 18 B under eval's entry", SP_ENTRY - low == 18,
          f"{SP_ENTRY - low}")

    # ------------------------------------------------------------------
    print("# --- E4 the NOT prefix's stack test ---")
    cl_not, oom_at = s["cl_not"], s["cl_not_oom"]
    hits[cl_not] = []
    hits[oom_at] = []
    ev("NOT0")
    sp_at = hits[cl_not][0]
    # stk_guard called at site SP S tests 2 B under it (its return address):
    # room iff CTLLIM + R < S - 2. cl_not must refuse from exactly that CTLLIM.
    want_first = sp_at - 2 - R
    first = None
    for c in range(want_first - 8, want_first + 8):
        hits[oom_at] = []
        ev("NOT0", c)
        if hits[oom_at]:
            first = c
            break
    check(f"cl_not refuses from CTLLIM ${want_first:04X}, stk_guard's floor at its SP",
          first == want_first, f"first={first}")
    hits[oom_at] = []
    de, fe, low, end = ev("NOT0", want_first)
    check("refused: ERR 7 deferred, DE = 0, cursor still on the NOT",
          fe == OOM and de == 0 and end == 0, f"FPERR={fe} DE={de:04X} end={end}")
    del hits[cl_not], hits[oom_at]
    chain = "NOT" * 80 + "0"           # 241 source bytes: under the 255 line
    seen_ok = seen_oom = False
    bad = []
    for c in range(SP_ENTRY - 300, EDGE_TOP, 8):
        de, fe, low, _ = ev(chain, c)
        if fe == 0:
            seen_ok = True
            if de != 0:
                bad.append((c, de, fe))
        elif fe == OOM:
            seen_oom = True
        else:
            bad.append((c, de, fe))
        if low <= c:
            bad.append((c, "SP", low))
    check("80 NOTs: 0 with room, ERR 7 without, the stack never at CTLLIM",
          seen_ok and seen_oom and not bad, f"ok={seen_ok} oom={seen_oom} bad={bad[:3]}")

    # ------------------------------------------------------------------
    print("# --- E5 every nested shape at the edge: right, or ERR 7 -- never below ---")
    for name, mk, _ in SHAPES:
        text = mk(8)
        want, fe0, low0, _ = ev(text)
        need = SP_ENTRY - low0
        seen_ok = seen_oom = False
        bad = []
        for c in range(SP_ENTRY - need - R - 12, EDGE_TOP, 4):
            de, fe, low, _ = ev(text, c)
            if fe == 0:
                seen_ok = True
                if de != want:
                    bad.append((c, de))
            elif fe == OOM:
                seen_oom = True
            else:
                bad.append((c, de, fe))
            if low <= c:
                bad.append((c, "SP", low))
        check(f"{name:6s} x8: right with room, ERR 7 without, never at CTLLIM",
              fe0 == 0 and seen_ok and seen_oom and not bad,
              f"ok={seen_ok} oom={seen_oom} bad={bad[:3]}")

    print()
    print(f"{'ALL PASS' if not fails else f'{fails} FAIL(S)'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
