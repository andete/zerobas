# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: string-compare S2 -- the six relational operators on two string
operands, plus the D-2 type-mismatch abort (repack build only).

Covers three layers:
  1. str_cmp_bits (basic/str-engine.asm) directly -- the unsigned-byte comparator's
     1/2/4 output for every §2 case (equal, prefix-shorter both directions, case,
     first-diff-byte both directions, empty-vs-nonempty both directions, both empty).
  2. The full ev_rel path via `eval` (basic/expr.asm) -- all six operators, the
     compound-form merge (<=/>=/<>), literal/variable/concat/nested-function
     operands, and the comparator-level type-mismatch signal (TMISMATCH/ERRMARK)
     for `A$<5` / `5<A$` / a bare string in numeric context.
  3. The statement-level abort (interp.asm/print.asm) -- IF/LET/PRINT each land on
     type_mismatch_error, print zerobas's own "type mismatch" message, and the
     REST OF THE LINE does not run (mirrors stmt_error's existing convention).

Like test_str_engine/test_str_verbs this builds basic/main-reloc.asm (ROM_BASE=
$2812) -- the lean 16 KB build has no string engine / no comparator and would fail
these by design (the whole feature is repack-only, spec-basic-string-compare.md).

Oracle basis:
- Comparison semantics (unsigned byte-by-byte, shorter-is-less, case-sensitive,
  §2 D-3) -- the standard MSX-BASIC string-ordering contract (public language
  reference), oracle-locked black-box on the Philips VG-8020
  (probes/basic/basic_probe_str_cmp.py; no disassembly).
- The relation-bit spine (relop_bit + the compound-form merge, cmp16_bits'
  1/2/4 encoding) is the EXISTING numeric ev_rel machinery (expr.asm), reused
  verbatim (spec §3).
- D-2 (type mismatch aborts the line, statement-level, own lowercase message) --
  spec-basic-string-compare.md §3c / §6.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = "/tmp/zb_strcmp.rom"
SYM = "/tmp/zb_strcmp.sym"
RELOC_BASE = 0x2812

SRC = 0xC000       # ASCII expression / line-body source
TOKBUF = 0xC100    # crunched-token buffer
SETSRC = 0xC300    # str_set_key source descriptor scratch
DESC_L = 0xC400    # scratch [len][bytes] descriptor (lhs, for direct str_cmp_bits)
DESC_R = 0xC480    # scratch [len][bytes] descriptor (rhs, for direct str_cmp_bits)


def build():
    src = os.path.join(ROOT, "basic", "main-reloc.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=RELOC_BASE)
    s = m.sym
    STRPTR = s["STRPTR"]
    VALTYP = s["VALTYP"]
    STRTAB = s["STRTAB"]
    STRENTSZ = s["STRENTSZ"]
    STRSLOTS = s["STRSLOTS"]
    ERRMARK = s["ERRMARK"]
    TMISMATCH = s["TMISMATCH"]

    fails = 0

    def check(label, cond, detail=""):
        nonlocal fails
        fails += not cond
        print(f"{'PASS' if cond else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))

    def reset_strtab():
        for i in range(STRSLOTS):
            m.poke(STRTAB + i * STRENTSZ, 0)

    def set_var(name, value):
        m.poke(SETSRC, bytes([len(value)]) + value)
        m.call("str_set_key", b=ord(name), c=0, de=SETSRC)

    def tok(text):
        m.poke(SRC, text.encode("ascii") + b"\x00")
        m.mem[TOKBUF:TOKBUF + 192] = b"\x00" * 192
        m.call("tokenise", hl=SRC, de=TOKBUF)

    def clear_markers():
        m.poke(ERRMARK, 0)
        m.poke(TMISMATCH, 0)

    def num_expr(text):
        """Evaluate a NUMERIC expression through the full ev_rel path -> DE."""
        tok(text)
        clear_markers()
        cpu = m.call("eval", hl=TOKBUF)
        return cpu.de & 0xFFFF

    def ck_num(label, got, want):
        check(f"{label} = {got} (want {want & 0xFFFF})", got == (want & 0xFFFF))

    # ------------------------------------------------------------------
    print("# --- str_cmp_bits: the unsigned-byte comparator (§2 D-3) ---")

    def desc(addr, data: bytes):
        m.poke(addr, bytes([len(data)]) + data)

    def cmp_bits(lhs: bytes, rhs: bytes):
        desc(DESC_L, lhs)
        desc(DESC_R, rhs)
        cpu = m.call("str_cmp_bits", hl=DESC_L, de=DESC_R, bc=0x1234)
        return cpu.a, cpu.bc

    def ck_bits(label, lhs, rhs, want_bit):
        a, bc = cmp_bits(lhs, rhs)
        ok = a == want_bit and bc == 0x1234
        detail = f"A={a} BC={bc:#06x}" if not ok else ""
        check(f"str_cmp_bits({lhs!r},{rhs!r}) = {a} (want {want_bit}, BC preserved)",
              ok, detail)

    ck_bits('"AB" vs "AB" (equal)', b"AB", b"AB", 2)
    ck_bits('"AB" vs "ABC" (prefix, shorter=lhs)', b"AB", b"ABC", 1)
    ck_bits('"ABC" vs "AB" (prefix, shorter=rhs)', b"ABC", b"AB", 4)
    ck_bits('"A" vs "a" (case, 0x41<0x61)', b"A", b"a", 1)
    ck_bits('"a" vs "A" (case, reversed)', b"a", b"A", 4)
    ck_bits('"ABD" vs "ABC" (first-diff-byte D>C)', b"ABD", b"ABC", 4)
    ck_bits('"ABC" vs "ABD" (first-diff-byte, reversed)', b"ABC", b"ABD", 1)
    ck_bits('"" vs "A" (empty is less)', b"", b"A", 1)
    ck_bits('"A" vs "" (empty is less, reversed)', b"A", b"", 4)
    ck_bits('"" vs "" (both empty, equal)', b"", b"", 2)

    # ------------------------------------------------------------------
    print("# --- full ev_rel path (eval): literals, all six operators ---")

    ck_num('"AB"="AB"', num_expr('"AB"="AB"'), -1)
    ck_num('"AB"<>"AB"', num_expr('"AB"<>"AB"'), 0)
    ck_num('"AB"<"ABC"', num_expr('"AB"<"ABC"'), -1)
    ck_num('"AB">"ABC"', num_expr('"AB">"ABC"'), 0)
    ck_num('"AB"<="ABC"', num_expr('"AB"<="ABC"'), -1)
    ck_num('"AB">="ABC"', num_expr('"AB">="ABC"'), 0)
    ck_num('"A"<"a"', num_expr('"A"<"a"'), -1)
    ck_num('"ABD">"ABC"', num_expr('"ABD">"ABC"'), -1)
    ck_num('""<"A"', num_expr('""<"A"'), -1)
    ck_num('""=""', num_expr('""=""'), -1)

    print("# --- compound-form merge (<=, >=, <>) on an EQUAL pair ---")
    ck_num('"A"<="A" (equal -> true)', num_expr('"A"<="A"'), -1)
    ck_num('"A">="A" (equal -> true)', num_expr('"A">="A"'), -1)
    ck_num('"A"<>"A" (equal -> false)', num_expr('"A"<>"A"'), 0)
    print("# --- compound-form merge on an ORDERED pair ---")
    ck_num('"B"<="A" (false)', num_expr('"B"<="A"'), 0)
    ck_num('"B">="A" (true)', num_expr('"B">="A"'), -1)

    print("# --- string VARIABLE operands ---")
    reset_strtab()
    set_var("A", b"AB")
    set_var("B", b"ABC")
    ck_num("A$<B$  A$=AB B$=ABC", num_expr("A$<B$"), -1)
    ck_num("A$=B$  A$=AB B$=ABC", num_expr("A$=B$"), 0)

    print("# --- concat / nested-function operands (spec nest) ---")
    ck_num('"A"+"B"="AB"', num_expr('"A"+"B"="AB"'), -1)
    ck_num('LEFT$("HELLO",3)="HEL"', num_expr('LEFT$("HELLO",3)="HEL"'), -1)
    reset_strtab()
    set_var("A", b"HE")
    set_var("B", b"LLO")
    ck_num("A$+B$=\"HELLO\"", num_expr('A$+B$="HELLO"'), -1)

    print("# --- boolean composition above ev_rel (AND/OR/NOT) ---")
    ck_num('("A"="A") AND ("B"="B")', num_expr('("A"="A") AND ("B"="B")'), -1)
    ck_num('("A"="A") AND ("B"="C")', num_expr('("A"="A") AND ("B"="C")'), 0)
    ck_num('NOT ("A"="B")', num_expr('NOT ("A"="B")'), -1)

    # ------------------------------------------------------------------
    print("# --- D-2 type mismatch: the comparator's own signal ---")

    def ck_mismatch(label, text, extra_setup=None):
        if extra_setup:
            extra_setup()
        got = num_expr(text)
        ok = (got == 0 and m.mem[ERRMARK] == 0xDD and m.mem[TMISMATCH] == 1)
        detail = "" if ok else f"DE={got} ERRMARK={m.mem[ERRMARK]:#04x} TMISMATCH={m.mem[TMISMATCH]}"
        check(f"{label}: DE=0, ERRMARK=$DD, TMISMATCH=1", ok, detail)

    ck_mismatch('"A"<5  (string LHS, numeric RHS)', '"A"<5')
    ck_mismatch('5<"A"  (numeric LHS, string RHS)', '5<"A"')
    reset_strtab()
    set_var("A", b"HI")
    ck_mismatch('A$<9  (string variable LHS)', "A$<9")
    ck_mismatch('9=A$  (string variable RHS)', "9=A$")
    ck_mismatch("A$  (bare string, no relop, in numeric context)", "A$")

    # control: a well-typed comparison must NOT set the markers.
    got = num_expr('"A"="A"')
    ok = got == 0xFFFF and m.mem[ERRMARK] == 0 and m.mem[TMISMATCH] == 0
    check('"A"="A" leaves ERRMARK/TMISMATCH clear (control)', ok,
          f"DE={got:#06x} ERRMARK={m.mem[ERRMARK]} TMISMATCH={m.mem[TMISMATCH]}")

    # ------------------------------------------------------------------
    print("# --- statement-level abort (ex_if / ex_let / PRINT-item) ---")

    def run_prog_cap(lines):
        """Store + RUN a small program, capturing CHPUT; screen BIOS stubbed out."""
        mm = Machine(ROM, SYM, rom_base=RELOC_BASE)
        mm.trap("BREAKX", lambda x: setattr(x.cpu, "f", x.cpu.f & ~0x01))
        for b in ("CHGMOD", "CHGCLR", "CLS", "ERAFNK", "DSPFNK"):
            mm.trap(b, lambda x: None)
        out = mm.capture_chput()
        mm.call("new_prog")
        for lineno, body in lines:
            mm.poke(SRC, body.encode("ascii") + b"\x00")
            mm.mem[TOKBUF:TOKBUF + 192] = b"\x00" * 192
            mm.call("tokenise", hl=SRC, de=TOKBUF)
            mm.call("store_line", bc=lineno, hl=TOKBUF)
        mm.call("run_prog")
        return mm, bytes(out)

    def var(mm, name):
        return mm.call("var_get_key", b=ord(name), c=0).de

    # IF <string vs number> THEN <clause>: the clause must NOT run, and the
    # program continues to the line below the offending one (mirrors stmt_error's
    # existing "ret to whoever called exec" convention -- an own-design divergence
    # from real MSX halting the whole run, pre-dating this slice).
    mm, out = run_prog_cap([
        (10, 'A$="HI"'),
        (20, "IF A$<5 THEN T=99"),
        (30, "U=7"),
    ])
    check("IF A$<5 THEN ...  prints 'type mismatch'", out == b"type mismatch\r\n",
          f"got {out!r}")
    check("IF A$<5 THEN ...  the THEN clause did not run (T stays 0)",
          var(mm, "T") == 0, f"T={var(mm,'T')}")
    check("IF A$<5 THEN ...  the NEXT line still runs (U=7)",
          var(mm, "U") == 7, f"U={var(mm,'U')}")

    # LET (numeric assignment): R=A$<5 must NOT assign R, and the rest of the
    # SAME line (after the ':') must NOT run either -- a full line abort.
    mm, out = run_prog_cap([
        (10, 'A$="HI"'),
        (20, "R=A$<5:U=88"),
        (30, "V=7"),
    ])
    check("R=A$<5:U=88  prints 'type mismatch'", out == b"type mismatch\r\n",
          f"got {out!r}")
    check("R=A$<5:U=88  R was not assigned", var(mm, "R") == 0, f"R={var(mm,'R')}")
    check("R=A$<5:U=88  the rest of the SAME line did not run (U stays 0)",
          var(mm, "U") == 0, f"U={var(mm,'U')}")
    check("R=A$<5:U=88  the NEXT stored line still runs (V=7)",
          var(mm, "V") == 7, f"V={var(mm,'V')}")

    # PRINT item: PRINT (A$<5) must print the message, not a numeric value.
    mm, out = run_prog_cap([
        (10, 'A$="HI"'),
        (20, "PRINT (A$<5)"),
    ])
    check("PRINT (A$<5)  prints 'type mismatch' (no numeric item)",
          out == b"type mismatch\r\n", f"got {out!r}")

    # Control: a well-typed IF/LET/PRINT must NOT print the mismatch message and
    # must behave normally (gating does not misfire on valid comparisons).
    mm, out = run_prog_cap([
        (10, 'A$="HI"'),
        (20, 'IF A$="HI" THEN T=99'),
    ])
    check("IF A$=\"HI\" THEN T=99 (valid) -> no mismatch message", out == b"",
          f"got {out!r}")
    check("IF A$=\"HI\" THEN T=99 (valid) -> T=99 (THEN ran)",
          var(mm, "T") == 99, f"T={var(mm,'T')}")

    print()
    print("ALL PASS — string-compare S2 (comparator + type mismatch)" if not fails
          else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
