# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: string engine S4 — the core string VERBS (repack build only).

Covers the eight S4 handlers (basic/str-engine.asm) wired through the gated
evaluator / PRINT / str_eval hooks:

  string -> number   LEN / ASC / VAL      (numeric factor: `eval`, read DE)
  number/str -> str  CHR$ / STR$ /
                     LEFT$ / RIGHT$ / MID$ (string operand: `str_eval`, read STRPTR)

Like test_str_engine (S3) this builds basic/main-reloc.asm (ROM_BASE=$2812) — the
lean 16 KB build has no verbs (its kwtable omits the keywords and its evaluator/
str_eval hooks fall through, byte-identical) and would fail these by design.

Oracle basis:
- Verb semantics (1-based MID$, LEFT$/RIGHT$ head/tail clamps, ASC "" = error,
  VAL leading-parse, STR$ leading blank for non-negatives) — public MSX-BASIC
  language reference. Divergences (integer-only VAL, CHR$ low-byte, STRMAX clamp,
  N=3 temp-ring depth) are own-design (docs/spec-basic-string-engine.md §3/§4/§6).
- Tokeniser crunches the keywords to $FF <selector> in the repack kwtable (S2/S3).
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

ROM = "/tmp/zb_strverbs.rom"
SYM = "/tmp/zb_strverbs.sym"
RELOC_BASE = 0x2812

SRC = 0xC000     # ASCII expression source
TOKBUF = 0xC100  # crunched-token buffer
SETSRC = 0xC300  # str_set_key source descriptor scratch


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

    fails = 0

    def reset_strtab():
        for i in range(STRSLOTS):
            m.poke(STRTAB + i * STRENTSZ, 0)

    def set_var(name, value):
        m.poke(SETSRC, bytes([len(value)]) + value)
        m.call("str_set_key", b=ord(name), c=0, de=SETSRC)

    def tok(text):
        m.poke(SRC, text.encode("ascii") + b"\x00")
        m.mem[TOKBUF:TOKBUF + 96] = b"\x00" * 96
        m.call("tokenise", hl=SRC, de=TOKBUF)

    def num_expr(text):
        """Evaluate a NUMERIC expression -> DE (unsigned 16)."""
        tok(text)
        cpu = m.call("eval", hl=TOKBUF)
        return cpu.de & 0xFFFF

    def str_expr(text):
        """Evaluate a STRING expression -> (cpu, len, bytes)."""
        tok(text)
        m.poke(VALTYP, 0)
        m.poke_w(STRPTR, 0)
        cpu = m.call("str_eval", hl=TOKBUF)
        ptr = m.mem[STRPTR] | (m.mem[STRPTR + 1] << 8)
        dlen = m.mem[ptr]
        dbytes = bytes(m.mem[ptr + 1: ptr + 1 + dlen])
        return cpu, dlen, dbytes

    def ck_num(label, got, want):
        nonlocal fails
        ok = (got == (want & 0xFFFF))
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label} = {got} (want {want & 0xFFFF})")

    def ck_str(label, res, want):
        nonlocal fails
        cpu, dlen, dbytes = res
        ok = carry(cpu) and m.mem[VALTYP] == 1 and dbytes == want and dlen == len(want)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label} = {dbytes!r} "
              f"(want {want!r}) CF={int(carry(cpu))} VALTYP={m.mem[VALTYP]}")

    print("# --- LEN / ASC / VAL (string -> number) ---")
    ck_num('LEN("HELLO")', num_expr('LEN("HELLO")'), 5)
    ck_num('LEN("")', num_expr('LEN("")'), 0)
    reset_strtab(); set_var("A", b"HI")
    ck_num('LEN(A$)  A$="HI"', num_expr("LEN(A$)"), 2)
    ck_num('LEN("A"+"BC")', num_expr('LEN("A"+"BC")'), 3)   # concat arg
    ck_num('ASC("A")', num_expr('ASC("A")'), 65)
    ck_num('ASC("Z")', num_expr('ASC("Z")'), 90)
    ck_num('VAL("123")', num_expr('VAL("123")'), 123)
    ck_num('VAL("-45")', num_expr('VAL("-45")'), -45)
    ck_num('VAL("+9")', num_expr('VAL("+9")'), 9)
    ck_num('VAL("  7")', num_expr('VAL("  7")'), 7)
    ck_num('VAL("12AB")', num_expr('VAL("12AB")'), 12)      # leading parse
    ck_num('VAL("ABC")', num_expr('VAL("ABC")'), 0)         # no digits
    ck_num('VAL("30000")', num_expr('VAL("30000")'), 30000)

    print("# --- CHR$ / STR$ (number -> string) ---")
    ck_str('CHR$(65)', str_expr("CHR$(65)"), b"A")
    ck_str('CHR$(90)', str_expr("CHR$(90)"), b"Z")
    ck_str('STR$(5)', str_expr("STR$(5)"), b" 5")           # leading blank
    ck_str('STR$(-3)', str_expr("STR$(-3)"), b"-3")
    ck_str('STR$(0)', str_expr("STR$(0)"), b" 0")
    ck_str('STR$(12345)', str_expr("STR$(12345)"), b" 12345")

    print("# --- LEFT$ / RIGHT$ / MID$ (substring) ---")
    ck_str('LEFT$("HELLO",3)', str_expr('LEFT$("HELLO",3)'), b"HEL")
    ck_str('LEFT$("HI",9)', str_expr('LEFT$("HI",9)'), b"HI")     # clamp
    ck_str('LEFT$("HI",0)', str_expr('LEFT$("HI",0)'), b"")       # empty
    ck_str('RIGHT$("HELLO",2)', str_expr('RIGHT$("HELLO",2)'), b"LO")
    ck_str('RIGHT$("HI",9)', str_expr('RIGHT$("HI",9)'), b"HI")   # clamp
    ck_str('RIGHT$("HELLO",0)', str_expr('RIGHT$("HELLO",0)'), b"")
    ck_str('MID$("HELLO",2,3)', str_expr('MID$("HELLO",2,3)'), b"ELL")
    ck_str('MID$("HELLO",2)', str_expr('MID$("HELLO",2)'), b"ELLO")     # to end
    ck_str('MID$("HELLO",3,99)', str_expr('MID$("HELLO",3,99)'), b"LLO")  # clamp count
    ck_str('MID$("HELLO",9,2)', str_expr('MID$("HELLO",9,2)'), b"")     # p beyond
    ck_str('MID$("HELLO",1,2)', str_expr('MID$("HELLO",1,2)'), b"HE")

    print("# --- composition (verbs + concat, the ring under pressure) ---")
    reset_strtab(); set_var("A", b"HE"); set_var("B", b"LLO")
    ck_str('LEFT$(A$+B$,3)  (spec nest)', str_expr("LEFT$(A$+B$,3)"), b"HEL")
    ck_str('"X"+CHR$(89)+"Z"', str_expr('"X"+CHR$(89)+"Z"'), b"XYZ")
    ck_str('"N="+STR$(5)', str_expr('"N="+STR$(5)'), b"N= 5")
    ck_str('MID$("ABCDEF",2,3)+"!"', str_expr('MID$("ABCDEF",2,3)+"!"'), b"BCD!")
    ck_num('LEN(LEFT$("HELLO",3))', num_expr('LEN(LEFT$("HELLO",3))'), 3)  # nested str fn in numeric

    print()
    print("ALL PASS — string engine S4 (verbs)" if not fails
          else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
