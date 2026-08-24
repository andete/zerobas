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
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

ROM = tp("zb_strverbs.rom")
SYM = tp("zb_strverbs.sym")
RELOC_BASE = 0x2812

SRC = 0xC000     # ASCII expression source
TOKBUF = 0xC100  # crunched-token buffer
SETSRC = 0xC300  # str_set_key source descriptor scratch ([len][ptr])
BODY = 0xC500    # scratch body the SETSRC descriptor points at (slice-4a heap)


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=RELOC_BASE)
    s = m.sym
    # Arrays slice-4b (docs/spec-basic-arrays-slice4b-scalar-reloc.md §2/Q3):
    # string-heap ops derive their array-region ceiling via ARYTAB (was
    # (PRGEND)+2). A fresh Machine zero-inits ALL RAM, so an unpoked PRGEND/
    # ARYTAB=0 makes that derivation land inside the SUB-ROM'S OWN CODE
    # BYTES -- a stride-walk over $FF padding can spin (near-)forever.
    # Placeholder-seed both (matching tests/test_arrays.py's own
    # convention) so any heap_alloc/strheap_gc this file triggers walks
    # harmless (empty) RAM instead.
    m.poke_w(s["PRGEND"], 0x9000)
    m.poke(0x9000, b"\x00\x00")
    m.poke_w(s["ARYTAB"], 0x9002)
    m.poke(0x9002, b"\x00\x00")
    # Arrays slice-4a (docs/spec-basic-arrays-slice4a-string-heap.md §2/§5):
    # in the repack build a string VALUE lives in the compacting heap and a
    # descriptor is [len:1][ptr:2]. heap_reset seeds FRETOP = min(HIMEM,TXTMAX)
    # (an empty heap) and TEMPTOP = TEMPBASE (an empty temp-descriptor stack),
    # exactly as clear_vars/NEW/RUN do at a real cold boot. Without it a fresh
    # Machine leaves FRETOP=0, so the first heap_alloc underflows and every
    # string comes back garbage.
    # D-CLP (docs/spec-basic-clearpool.md): the string heap's floor is now the
    # POOL FLOOR, `min(HIMEM,TXTMAX) - POOLSIZE`, so an unseeded POOLSIZE of 0
    # is a ZERO-BYTE POOL and every allocation below fails with `Out of string
    # space`. heap_reset does NOT seed it -- the real cold boot sets it in
    # basic/interp.asm `init`, ahead of clear_vars, and NEW/RUN/a bare CLEAR all
    # deliberately keep whatever size is current. This poke is this harness's
    # stand-in for that boot step, sized like a `CLEAR 4096` rather than the
    # faithful 200 because these cases allocate freely and the subject under
    # test is the string engine, not the pool.
    m.poke_w(s["POOLSIZE"], 4096)
    m.call("heap_reset")
    STRPTR = s["STRPTR"]
    VALTYP = s["VALTYP"]
    TEMPBASE = s["TEMPBASE"]
    TEMPTOP = s["TEMPTOP"]

    fails = 0

    def read_val(addr):
        """Read a [len:1][ptr:2] descriptor -> the body bytes it points at.
        Slice-4a heap format: the value bytes live at ptr, NOT inline after
        len (that was the pre-4a [len][bytes] convention)."""
        dlen = m.mem[addr]
        if dlen == 0:
            return 0, b""
        bptr = m.mem[addr + 1] | (m.mem[addr + 2] << 8)
        return dlen, bytes(m.mem[bptr: bptr + dlen])

    def reset_strtab():
        # Arrays slice-4c (§3d): string scalars are chain-resident now
        # (STRTAB is gone) -- re-anchor ARYTAB to the scalar-region base
        # and rewrite the "no arrays" sentinel there (mirrors the initial
        # setup's ARYTAB poke above; the vars_reset/ary_reset equivalent).
        m.poke_w(s["ARYTAB"], 0x9002)
        m.poke(0x9002, b"\x00\x00")

    def stmt_boundary():
        """Mirror exec_stmt (interp.asm): empty the temp-descriptor stack at
        each statement boundary so temps never accumulate across the many
        expressions this test evaluates directly (str_eval/eval bypass
        exec_stmt, which is where the ROM does this reset)."""
        m.poke_w(TEMPTOP, TEMPBASE)

    def set_var(name, value):
        # A str_set_key source is a STABLE [len][ptr] descriptor (slice-4a §10):
        # sh_var_store reads len from (SETSRC) then follows ptr to copy the body
        # into a fresh heap allocation. Point ptr at a scratch body buffer.
        m.poke(BODY, value)
        m.poke(SETSRC, bytes([len(value)]))
        m.poke_w(SETSRC + 1, BODY)
        m.call("str_set_key", b=ord(name), c=0, de=SETSRC)

    def tok(text):
        m.poke(SRC, text.encode("ascii") + b"\x00")
        m.mem[TOKBUF:TOKBUF + 96] = b"\x00" * 96
        m.call("tokenise", hl=SRC, de=TOKBUF)

    def num_expr(text):
        """Evaluate a NUMERIC expression -> DE (unsigned 16)."""
        tok(text)
        stmt_boundary()
        cpu = m.call("eval", hl=TOKBUF)
        return cpu.de & 0xFFFF

    def str_expr(text):
        """Evaluate a STRING expression -> (cpu, len, bytes)."""
        tok(text)
        stmt_boundary()
        m.poke(VALTYP, 0)
        m.poke_w(STRPTR, 0)
        cpu = m.call("str_eval", hl=TOKBUF)
        ptr = m.mem[STRPTR] | (m.mem[STRPTR + 1] << 8)
        dlen, dbytes = read_val(ptr)
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
