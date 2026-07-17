# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: string-functions S2 — HEX$/OCT$/SPACE$/STRING$/INSTR (repack
build only), docs/spec-basic-string-functions.md.

Covers all three integration shapes (spec §3):
  Group A ($FF-prefixed, string->string): HEX$, OCT$, SPACE$ — via str_func_ff,
    reached the same way as CHR$/STR$/LEFT$/RIGHT$/MID$ (test_str_verbs.py).
  Group B (single-byte token $E3, string->string): STRING$ — via str_eval's
    entry dispatch (basic/strvar.asm).
  Group C (single-byte token $E5, string->number): INSTR — via ev_f
    (basic/expr.asm), the numeric factor path.

Like test_str_engine/test_str_verbs/test_str_compare this builds
basic/main-reloc.asm (ROM_BASE=$2812) — the lean 16 KB build has no string
engine (kwtable omits the five keywords; the evaluator/str_eval/ev_f hooks are
gated out, byte-identical) and would fail these by design.

Oracle basis:
- Token widths/values (HEX$=$FF$9B, OCT$=$FF$9A, SPACE$=$FF$99, STRING$=$E3,
  INSTR=$E5) — black-box VG-8020 crunch capture (S2), cross-checked vs MSX2 TH
  Table 2.20 (equates in sysvars.inc).
- Verb semantics (unsigned-16 HEX$/OCT$ text, STRING$'s numeric-code-vs-
  string-first-byte dual form, INSTR's 1-based search / empty-needle / p<1)
  — public MSX-BASIC language reference. Divergences (STRMAX clamp on
  SPACE$/STRING$, negative-length error, N=3 ring reuse for INSTR's two
  snapshots) are own-design (spec §6 D-2..D-6).
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

ROM = "/tmp/zb_strfn.rom"
SYM = "/tmp/zb_strfn.sym"
RELOC_BASE = 0x2812

SRC = 0xC000     # ASCII expression source
TOKBUF = 0xC100  # crunched-token buffer
SETSRC = 0xC300  # str_set_key source descriptor scratch ([len][ptr])
BODY = 0xC500    # scratch body the SETSRC descriptor points at (slice-4a heap)


def build():
    src = os.path.join(ROOT, "basic", "main-reloc.asm")
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
    # a repack-build string VALUE lives in the compacting heap and a descriptor
    # is [len:1][ptr:2]. heap_reset seeds FRETOP (empty heap) + TEMPTOP (empty
    # temp-descriptor stack) exactly as a real cold boot does, so the string
    # functions have somewhere to allocate their result bodies.
    m.call("heap_reset")
    STRPTR = s["STRPTR"]
    VALTYP = s["VALTYP"]
    STRTAB = s["STRTAB"]
    STRENTSZ = s["STRENTSZ"]
    STRSLOTS = s["STRSLOTS"]
    ERRMARK = s["ERRMARK"]
    STRMAX = s["STRMAX"]     # 255 in the repack build (slice-4a widened 64->255)
    TEMPBASE = s["TEMPBASE"]
    TEMPTOP = s["TEMPTOP"]

    fails = 0

    def read_val(addr):
        """Read a [len:1][ptr:2] descriptor -> the heap body bytes it points
        at (slice-4a: value bytes are no longer inline after len)."""
        dlen = m.mem[addr]
        if dlen == 0:
            return 0, b""
        bptr = m.mem[addr + 1] | (m.mem[addr + 2] << 8)
        return dlen, bytes(m.mem[bptr: bptr + dlen])

    def reset_strtab():
        for i in range(STRSLOTS):
            m.poke(STRTAB + i * STRENTSZ, 0)

    def stmt_boundary():
        """Mirror exec_stmt (interp.asm): empty the temp-descriptor stack at
        each statement boundary so temps don't accumulate across the many
        direct str_eval/eval calls this test makes (they bypass exec_stmt)."""
        m.poke_w(TEMPTOP, TEMPBASE)

    def set_var(name, value):
        # str_set_key source = a STABLE [len][ptr] descriptor (slice-4a §10):
        # sh_var_store follows ptr to copy the body into a fresh heap alloc.
        m.poke(BODY, value)
        m.poke(SETSRC, bytes([len(value)]))
        m.poke_w(SETSRC + 1, BODY)
        m.call("str_set_key", b=ord(name), c=0, de=SETSRC)

    def tok(text):
        m.poke(SRC, text.encode("ascii") + b"\x00")
        m.mem[TOKBUF:TOKBUF + 192] = b"\x00" * 192
        m.call("tokenise", hl=SRC, de=TOKBUF)

    def clear_markers():
        m.poke(ERRMARK, 0)

    def num_expr(text):
        """Evaluate a NUMERIC expression -> DE (unsigned 16)."""
        tok(text)
        clear_markers()
        stmt_boundary()
        cpu = m.call("eval", hl=TOKBUF)
        return cpu.de & 0xFFFF

    def str_expr(text):
        """Evaluate a STRING expression -> (cpu, len, bytes)."""
        tok(text)
        clear_markers()
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

    def ck_str_err(label, res):
        """A malformed/erroring string call -> CF clear (str_eval_no)."""
        nonlocal fails
        cpu, dlen, dbytes = res
        ok = not carry(cpu)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label} -> CF clear (rejected) "
              f"CF={int(carry(cpu))}")

    print(f"# STRMAX = {STRMAX}")

    # ------------------------------------------------------------------
    print("# --- Group A: HEX$ (unsigned-16 hex text, no leading zeros) ---")
    ck_str('HEX$(0)', str_expr("HEX$(0)"), b"0")
    ck_str('HEX$(255)', str_expr("HEX$(255)"), b"FF")
    ck_str('HEX$(65535)', str_expr("HEX$(65535)"), b"FFFF")
    ck_str('HEX$(-1)', str_expr("HEX$(-1)"), b"FFFF")
    ck_str('HEX$(16)', str_expr("HEX$(16)"), b"10")
    ck_str('HEX$(4096)', str_expr("HEX$(4096)"), b"1000")
    ck_str('HEX$(1)', str_expr("HEX$(1)"), b"1")

    print("# --- Group A: OCT$ (unsigned-16 octal text, no leading zeros) ---")
    ck_str('OCT$(8)', str_expr("OCT$(8)"), b"10")
    ck_str('OCT$(-1)', str_expr("OCT$(-1)"), b"177777")
    ck_str('OCT$(0)', str_expr("OCT$(0)"), b"0")
    ck_str('OCT$(7)', str_expr("OCT$(7)"), b"7")
    ck_str('OCT$(64)', str_expr("OCT$(64)"), b"100")

    print("# --- Group A: SPACE$ ---")
    ck_str('SPACE$(0)', str_expr("SPACE$(0)"), b"")
    ck_str('SPACE$(3)', str_expr("SPACE$(3)"), b"   ")
    ck_str(f'SPACE$({STRMAX + 20}) clamp', str_expr(f"SPACE$({STRMAX + 20})"),
           b" " * STRMAX)
    ck_str_err('SPACE$(-1) negative -> error', str_expr("SPACE$(-1)"))

    # Regression: SPACE$ must fill EXACTLY `count` bytes, not overrun its buffer.
    # The original (pre-4a) fill loop did `ld b,0 : djnz`, writing 256 bytes
    # regardless of count and smearing the sysvars above the old STRTMP ring —
    # invisible to the descriptor-length checks above (they read only `count`
    # bytes) but it corrupted TMISMATCH and surfaced as a spurious "type
    # mismatch" live. Slice-4a retired the ring: a SPACE$ result now owns a
    # freshly heap_alloc'd body of exactly `count` bytes (sh_fill), so the
    # heap-model equivalent of the guard is "nothing BELOW the body (into the
    # rest of the free heap, where an over-fill would spill) became a space".
    # Seed a non-space sentinel across the heap span just under FRETOP, run
    # SPACE$(2), then assert the body is exactly two spaces and the sentinel
    # bytes below it are untouched.
    FRETOP = s["FRETOP"]
    SENT = 0xAA
    ceil = m.mem[FRETOP] | (m.mem[FRETOP + 1] << 8)
    for a in range(ceil - 64, ceil):
        m.poke(a, SENT)
    res = str_expr("SPACE$(2)")
    ptr = m.mem[STRPTR] | (m.mem[STRPTR + 1] << 8)
    bptr = m.mem[ptr + 1] | (m.mem[ptr + 2] << 8)     # SPACE$ result body address
    below = m.mem[bptr - 40: bptr]                     # heap bytes just below the body
    overran = any(b == 0x20 for b in below)
    fills2 = res[1] == 2 and res[2] == b"  "
    ok = fills2 and not overran
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  SPACE$(2) fills exactly 2 (no heap overrun) "
          f"len={res[1]} below_has_space={overran}")

    # ------------------------------------------------------------------
    print("# --- Group B: STRING$ (numeric code / string first byte / clamp) ---")
    ck_str('STRING$(3,65)  (numeric code)', str_expr("STRING$(3,65)"), b"AAA")
    ck_str('STRING$(3,"*")  (string fill)', str_expr('STRING$(3,"*")'), b"***")
    ck_str('STRING$(3,"abc")  (first byte)', str_expr('STRING$(3,"abc")'), b"aaa")
    ck_str('STRING$(0,65)', str_expr("STRING$(0,65)"), b"")
    ck_str(f'STRING$({STRMAX + 20},88) clamp', str_expr(f"STRING$({STRMAX + 20},88)"),
           b"X" * STRMAX)
    ck_str_err('STRING$(3,"") empty x$ -> error', str_expr('STRING$(3,"")'))
    ck_str_err('STRING$(-1,65) negative -> error', str_expr("STRING$(-1,65)"))
    reset_strtab()
    set_var("A", b"Q")
    ck_str('STRING$(4,A$)  A$="Q"', str_expr("STRING$(4,A$)"), b"QQQQ")

    print("# --- Group B: STRING$ composes with concat ---")
    ck_str('"["+STRING$(3,45)+"]"', str_expr('"["+STRING$(3,45)+"]"'), b"[---]")

    # ------------------------------------------------------------------
    print("# --- Group C: INSTR (2-arg form, default p=1) ---")
    ck_num('INSTR("HELLO","LL")', num_expr('INSTR("HELLO","LL")'), 3)
    ck_num('INSTR("HELLO","H")', num_expr('INSTR("HELLO","H")'), 1)
    ck_num('INSTR("HELLO","O")', num_expr('INSTR("HELLO","O")'), 5)
    ck_num('INSTR("HELLO","X")  not found', num_expr('INSTR("HELLO","X")'), 0)
    ck_num('INSTR("HELLO","HELLO!")  needle longer', num_expr('INSTR("HELLO","HELLO!")'), 0)
    ck_num('INSTR("HELLO","")  empty needle -> p(=1)', num_expr('INSTR("HELLO","")'), 1)
    ck_num('INSTR("","")  both empty -> 1', num_expr('INSTR("","")'), 1)
    ck_num('INSTR("","X")  empty haystack', num_expr('INSTR("","X")'), 0)

    print("# --- Group C: INSTR (3-arg form, explicit p) ---")
    ck_num('INSTR(2,"HELLO","L")  p mid', num_expr('INSTR(2,"HELLO","L")'), 3)
    ck_num('INSTR(4,"HELLO","L")  p mid, 2nd L', num_expr('INSTR(4,"HELLO","L")'), 4)
    ck_num('INSTR(5,"HELLO","L")  p past last L', num_expr('INSTR(5,"HELLO","L")'), 0)
    ck_num('INSTR(9,"HELLO","H")  p past end', num_expr('INSTR(9,"HELLO","H")'), 0)
    ck_num('INSTR(6,"HELLO","")  empty needle, p at len+1',
           num_expr('INSTR(6,"HELLO","")'), 6)
    ck_num('INSTR(9,"HELLO","")  empty needle, p past len+1 clamps',
           num_expr('INSTR(9,"HELLO","")'), 6)
    ck_num('INSTR(1,"HELLO","HELLO")  full match', num_expr('INSTR(1,"HELLO","HELLO")'), 1)

    print("# --- Group C: INSTR overlapping matches ---")
    ck_num('INSTR("AAAA","AA")  first', num_expr('INSTR("AAAA","AA")'), 1)
    ck_num('INSTR(2,"AAAA","AA")  overlap from p=2', num_expr('INSTR(2,"AAAA","AA")'), 2)
    ck_num('INSTR(3,"AAAA","AA")  overlap from p=3', num_expr('INSTR(3,"AAAA","AA")'), 3)
    ck_num('INSTR(4,"AAAA","AA")  no room left', num_expr('INSTR(4,"AAAA","AA")'), 0)

    print("# --- Group C: INSTR p<1 -> function error (ERRMARK) ---")
    clear_markers()
    got = num_expr('INSTR(0,"HELLO","L")')
    ok = got == 0 and m.mem[ERRMARK] == 0xDD
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  INSTR(0,...) p=0 -> DE=0, ERRMARK=$DD "
          f"(got DE={got}, ERRMARK={m.mem[ERRMARK]:#04x})")
    clear_markers()
    got = num_expr('INSTR(-1,"HELLO","L")')
    ok = got == 0 and m.mem[ERRMARK] == 0xDD
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  INSTR(-1,...) p<0 -> DE=0, ERRMARK=$DD "
          f"(got DE={got}, ERRMARK={m.mem[ERRMARK]:#04x})")

    print("# --- Group C: INSTR with variable / concat operands ---")
    reset_strtab()
    set_var("A", b"HELLO")
    set_var("B", b"LL")
    ck_num("INSTR(A$,B$)  A$=HELLO B$=LL", num_expr("INSTR(A$,B$)"), 3)
    ck_num('INSTR("X"+A$,B$)  concat lhs', num_expr('INSTR("X"+A$,B$)'), 4)

    print()
    print("ALL PASS — string-functions S2 (HEX$/OCT$/SPACE$/STRING$/INSTR)" if not fails
          else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
