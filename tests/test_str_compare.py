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
     operands, and the comparator-level type-mismatch signal (FPERR/ERRMARK)
     for `A$<5` / `5<A$` / a bare string in numeric context. D-PENDERR
     (docs/spec-basic-penderr.md): that signal used to be a dedicated 1-byte
     TMISMATCH flag set to 1; it is now the pending-error CODE cell FPERR set to
     FPERR_TYPEMM (10), which fperr_to_err maps to the same ERR 13. These
     assertions are the host-side proof of exactly that mapping.
  3. The statement-level abort (interp.asm/print.asm) -- IF/LET/PRINT each land on
     type_mismatch_error, print zerobas's own "Type mismatch" message, and the
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

Also covers the unparenthesized-PRINT-lead follow-on slice
(spec-basic-print-unparen-compare.md, its own S2): `PRINT A$="YES"` and friends
(var/literal/function/concat leads, all six operators, the D-2 abort, and a
plain-PRINT regression watch) -- the dispatch decision (`exp_strvar` /
`exp_maybe_strfn`'s `relop_peek` gate in print.asm/str-engine.asm) and the
printed bytes are both BIOS-independent (CHPUT is trapped, not the real BIOS),
so the full behaviour is exercised here; the openMSX probe
(basic_probe_str_cmp.py) additionally reference-locks it on real hardware.
"""

import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = tp("zb_strcmp.rom")
SYM = tp("zb_strcmp.sym")
RELOC_BASE = 0x2812

SRC = 0xC000       # ASCII expression / line-body source
TOKBUF = 0xC100    # crunched-token buffer
SETSRC = 0xC300    # str_set_key source descriptor scratch ([len][ptr])
DESC_L = 0xC400    # scratch [len][ptr] descriptor (lhs, for direct str_cmp_bits)
DESC_R = 0xC480    # scratch [len][ptr] descriptor (rhs, for direct str_cmp_bits)
LBODY = 0xC500     # body the DESC_L descriptor points at (slice-4a heap format)
RBODY = 0xC580     # body the DESC_R descriptor points at
BODY = 0xC600      # body the SETSRC descriptor points at (set_var)


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
    # harmless (empty) RAM instead. (The OTHER Machine this file builds,
    # run_prog_cap's `mm`, calls new_prog for real and needs no such seed.)
    m.poke_w(s["PRGEND"], 0x9000)
    m.poke(0x9000, b"\x00\x00")
    m.poke_w(s["ARYTAB"], 0x9002)
    m.poke(0x9002, b"\x00\x00")
    # Arrays slice-4a (docs/spec-basic-arrays-slice4a-string-heap.md §2/§5): a
    # repack-build string VALUE lives in the compacting heap; a descriptor is
    # [len:1][ptr:2] (the comparator dereferences ptr on both sides). heap_reset
    # seeds FRETOP (empty heap) + TEMPTOP (empty temp stack) as a real cold boot
    # does, so str_eval's operand snapshots have somewhere to allocate -- without
    # it same-length operands' bodies deref to garbage and every == misfires.
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
    ERRMARK = s["ERRMARK"]
    FPERR = s["FPERR"]
    FPERR_TYPEMM = 10       # sysvars.inc; -> ERR 13 via interp.asm fperr_to_err
    TEMPBASE = s["TEMPBASE"]
    TEMPTOP = s["TEMPTOP"]

    fails = 0

    def check(label, cond, detail=""):
        nonlocal fails
        fails += not cond
        print(f"{'PASS' if cond else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))

    def reset_strtab():
        # Arrays slice-4c (§3d): string scalars are chain-resident now
        # (STRTAB is gone) -- re-anchor ARYTAB to the scalar-region base
        # and rewrite the "no arrays" sentinel there (mirrors the initial
        # setup's ARYTAB poke above; the vars_reset/ary_reset equivalent).
        m.poke_w(s["ARYTAB"], 0x9002)
        m.poke(0x9002, b"\x00\x00")

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
        m.poke(FPERR, 0)

    def num_expr(text):
        """Evaluate a NUMERIC expression through the full ev_rel path -> DE.
        Resets the temp stack first (exec_stmt's per-statement boundary, which
        the direct eval call bypasses) so operand snapshots don't accumulate."""
        tok(text)
        clear_markers()
        m.poke_w(TEMPTOP, TEMPBASE)
        cpu = m.call("eval", hl=TOKBUF)
        return cpu.de & 0xFFFF

    def ck_num(label, got, want):
        check(f"{label} = {got} (want {want & 0xFFFF})", got == (want & 0xFFFF))

    # ------------------------------------------------------------------
    print("# --- str_cmp_bits: the unsigned-byte comparator (§2 D-3) ---")

    def desc(addr, body_addr, data: bytes):
        # slice-4a: a descriptor is [len:1][ptr:2]; str_cmp_bits dereferences
        # ptr on both operands, so the value bytes live at body_addr, not inline.
        m.poke(body_addr, data)
        m.poke(addr, bytes([len(data)]))
        m.poke_w(addr + 1, body_addr)

    def cmp_bits(lhs: bytes, rhs: bytes):
        desc(DESC_L, LBODY, lhs)
        desc(DESC_R, RBODY, rhs)
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
        ok = (got == 0 and m.mem[ERRMARK] == 0xDD and m.mem[FPERR] == FPERR_TYPEMM)
        detail = "" if ok else f"DE={got} ERRMARK={m.mem[ERRMARK]:#04x} FPERR={m.mem[FPERR]}"
        check(f"{label}: DE=0, ERRMARK=$DD, FPERR=10", ok, detail)

    ck_mismatch('"A"<5  (string LHS, numeric RHS)', '"A"<5')
    ck_mismatch('5<"A"  (numeric LHS, string RHS)', '5<"A"')
    reset_strtab()
    set_var("A", b"HI")
    ck_mismatch('A$<9  (string variable LHS)', "A$<9")
    ck_mismatch('9=A$  (string variable RHS)', "9=A$")
    ck_mismatch("A$  (bare string, no relop, in numeric context)", "A$")

    # control: a well-typed comparison must NOT set the markers.
    got = num_expr('"A"="A"')
    ok = got == 0xFFFF and m.mem[ERRMARK] == 0 and m.mem[FPERR] == 0
    check('"A"="A" leaves ERRMARK/FPERR clear (control)', ok,
          f"DE={got:#06x} ERRMARK={m.mem[ERRMARK]} FPERR={m.mem[FPERR]}")

    # ------------------------------------------------------------------
    print("# --- statement-level abort (ex_if / ex_let / PRINT-item) ---")

    def run_prog_cap(lines):
        """Store + RUN a small program, capturing CHPUT; screen BIOS stubbed out."""
        mm = Machine(ROM, SYM, rom_base=RELOC_BASE)
        # D-CLP: same cold-boot stand-in as the main machine above -- this helper
        # builds its OWN Machine and reaches heap_reset through run_prog's
        # clear_vars, which does not (and must not) touch POOLSIZE. Left at 0 the
        # pool is zero bytes wide and even `A$="HI"` on line 10 dies with
        # `out of string space in 10`, which is a true report about an unbooted
        # machine and tells you nothing about string COMPARISON.
        mm.poke_w(mm.sym["POOLSIZE"], 4096)
        mm.trap("BREAKX", lambda x: setattr(x.cpu, "f", x.cpu.f & ~0x01))
        for b in ("CHGMOD", "CHGCLR", "CLS", "ERAFNK", "DSPFNK"):
            mm.trap(b, lambda x: None)
        out = mm.capture_chput()
        mm.call("new_prog")
        for lineno, body in lines:
            mm.poke(SRC, body.encode("ascii") + b"\x00")
            mm.mem[TOKBUF:TOKBUF + 192] = b"\x00" * 192
            mm.call("tokenise", hl=SRC, de=TOKBUF)
    # 🔴 D-TXTCEIL: `store_line` now bounds the store against `SL_CEIL`, a RAM
    # cell that `dl_store` publishes on the real machine (from fch_ctx_addr(1) =
    # strheap_varceil). These tests call `store_line` DIRECTLY, so they must
    # supply it too -- without it the cell is 0 in this harness's zeroed RAM,
    # every store is refused as OOM, and the abort funnel does `ld sp,(SAVSTK)`
    # with SAVSTK=0 and runs away (msxtest.StackLost). The value is TXTMAX, which
    # is exactly the CONSTANT the code compared against before, so these rows go
    # on testing what they tested.
            mm.poke_w(mm.sym["SL_CEIL"], mm.sym["TXTMAX"])
            mm.call("store_line", bc=lineno, hl=TOKBUF)
        # 🔴 D-SPMERGE step 4: `rp_lp` re-bases the machine stack on the pool
        # frontier (`ld sp,(CSP)`) on every pass -- that is what makes the pool's
        # free sites symmetric. On a real machine `ctl_reset` publishes `CSP` at
        # cold boot before anything runs (MEASURED 2026-09-12: ctl_reset at t=2.641
        # and t=2.656, first `repl` at t=2.713 with CSP=D906 already), but it
        # derives the value through a SUB-ROM call this harness does not have, so
        # here it only gets as far as its own `CSP := 0` -- and `ld sp,(CSP)` then
        # takes SP to 0 and the CPU runs away. Standing in for the boot is the same
        # fix D-TXTCEIL made for `SL_CEIL`: supply what the machine publishes. The
        # value only has to sit in the harness's stack band [0x8000,0xf380].
        mm.trap("ctl_reset", lambda mm: (mm.poke_w(mm.sym["CSP"], 0xF000),
                                           mm.poke_w(mm.sym["CTLLIM"], 0x8000)))
        mm.call("run_prog")
        return mm, bytes(out)

    def var(mm, name):
        # F3 S3a (docs/spec-basic-float-core.md §11): numeric variables are now
        # TYPED, keyed on (name, resolved type) with variable-width entries: an
        # unsuffixed name like T/U/V/R defaults to DOUBLE. var_get_key still
        # exists (byte-identical, lean-build-only int accessor) but no longer
        # matches the repack build's actual storage shape, so probing it directly
        # here would misread past the [type] byte this slice inserted. Read
        # through var_load_fac instead (BC=key, A=8=double), which returns the
        # variable's int16 fast-path value exactly like every other float-aware
        # int consumer (ev_f_var, PRINT, ...).
        return mm.call("var_load_fac", a=8, b=ord(name), c=0).de

    # IF <string vs number> THEN <clause>: the clause must NOT run, AND the whole
    # RUN aborts to the prompt -- the line below the offending one does NOT run.
    # (Error-handling arc S1, D-1, docs/spec-basic-error-handling.md: an untrapped
    # runtime error now aborts the RUN, matching real MSX. This REVERSES the
    # earlier own-design "continue to the next line" divergence that this test used
    # to assert; the type-mismatch here funnels through fre_abort_low, which now
    # sets ENDFLAG.) S1 D-2 further appends " in <line>" in RUN mode, so the message
    # is "type mismatch in 20" (the error is on line 20 in each program below).
    mm, out = run_prog_cap([
        (10, 'A$="HI"'),
        (20, "IF A$<5 THEN T=99"),
        (30, "U=7"),
    ])
    check("IF A$<5 THEN ...  prints 'Type mismatch'", out == b"Type mismatch in 20\r\n",
          f"got {out!r}")
    check("IF A$<5 THEN ...  the THEN clause did not run (T stays 0)",
          var(mm, "T") == 0, f"T={var(mm,'T')}")
    check("IF A$<5 THEN ...  the RUN aborts, the NEXT line does NOT run (U stays 0)",
          var(mm, "U") == 0, f"U={var(mm,'U')}")

    # LET (numeric assignment): R=A$<5 must NOT assign R, the rest of the SAME line
    # (after the ':') must NOT run, AND the RUN aborts -- the next stored line does
    # not run either (D-1, as above).
    mm, out = run_prog_cap([
        (10, 'A$="HI"'),
        (20, "R=A$<5:U=88"),
        (30, "V=7"),
    ])
    check("R=A$<5:U=88  prints 'Type mismatch'", out == b"Type mismatch in 20\r\n",
          f"got {out!r}")
    check("R=A$<5:U=88  R was not assigned", var(mm, "R") == 0, f"R={var(mm,'R')}")
    check("R=A$<5:U=88  the rest of the SAME line did not run (U stays 0)",
          var(mm, "U") == 0, f"U={var(mm,'U')}")
    check("R=A$<5:U=88  the RUN aborts, the NEXT stored line does NOT run (V stays 0)",
          var(mm, "V") == 0, f"V={var(mm,'V')}")

    # PRINT item: PRINT (A$<5) must print the message, not a numeric value.
    mm, out = run_prog_cap([
        (10, 'A$="HI"'),
        (20, "PRINT (A$<5)"),
    ])
    check("PRINT (A$<5)  prints 'Type mismatch' (no numeric item)",
          out == b"Type mismatch in 20\r\n", f"got {out!r}")

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

    # ------------------------------------------------------------------
    print("# --- S2 (print-unparen-compare): unparenthesized PRINT-lead "
          "comparisons, all three leads ---")

    mm, out = run_prog_cap([
        (10, 'A$="YES"'),
        (20, 'PRINT A$="YES"'),
    ])
    check('PRINT A$="YES"  (var lead, true) -> "-1 "', out == b"-1 \r\n", f"got {out!r}")

    mm, out = run_prog_cap([
        (10, 'A$="YES"'),
        (20, 'PRINT A$="NO"'),
    ])
    check('PRINT A$="NO"  (var lead, false) -> " 0 "', out == b" 0 \r\n", f"got {out!r}")

    mm, out = run_prog_cap([
        (10, 'A$="AB"'),
        (20, 'B$="ABC"'),
        (30, "PRINT A$<B$"),
    ])
    check('PRINT A$<B$  (var lead, var RHS, ordering) -> "-1 "',
          out == b"-1 \r\n", f"got {out!r}")

    mm, out = run_prog_cap([
        (10, 'A$="AB"'),
        (20, 'B$="AB"'),
        (30, "PRINT A$<=B$"),
    ])
    check('PRINT A$<=B$  (var lead, compound form <=, equal) -> "-1 "',
          out == b"-1 \r\n", f"got {out!r}")

    mm, out = run_prog_cap([
        (10, 'A$="AB"'),
        (20, 'B$="AB"'),
        (30, "PRINT A$<>B$"),
    ])
    check('PRINT A$<>B$  (var lead, compound form <>, equal -> false) -> " 0 "',
          out == b" 0 \r\n", f"got {out!r}")

    mm, out = run_prog_cap([
        (10, 'A$="YES"'),
        (20, 'PRINT "YES"=A$'),
    ])
    check('PRINT "YES"=A$  (literal lead, var RHS) -> "-1 "',
          out == b"-1 \r\n", f"got {out!r}")

    mm, out = run_prog_cap([
        (10, 'PRINT "a"<"b"'),
    ])
    check('PRINT "a"<"b"  (literal lead, literal RHS) -> "-1 "',
          out == b"-1 \r\n", f"got {out!r}")

    mm, out = run_prog_cap([
        (10, 'A$="HELLO"'),
        (20, 'PRINT LEFT$(A$,1)="H"'),
    ])
    check('PRINT LEFT$(A$,1)="H"  (function lead) -> "-1 "',
          out == b"-1 \r\n", f"got {out!r}")

    mm, out = run_prog_cap([
        (10, 'A$="HE"'),
        (20, 'B$="LLO"'),
        (30, 'PRINT A$+B$="HELLO"'),
    ])
    check('PRINT A$+B$="HELLO"  (concat-chain lead) -> "-1 "',
          out == b"-1 \r\n", f"got {out!r}")

    # D-2: the bare, UNPARENTHESIZED form aborts with 'type mismatch' and
    # prints NOTHING for the item itself -- before this slice, exp_loop
    # mis-dispatched this to exp_strvar's plain-print path, so A$'s value
    # printed first and a syntax error followed (spec §2 background).
    mm, out = run_prog_cap([
        (10, 'A$="HI"'),
        (20, "PRINT A$<5"),
    ])
    check("PRINT A$<5  (bare, unparenthesized) prints 'Type mismatch', "
          "NOT A$'s value", out == b"Type mismatch in 20\r\n", f"got {out!r}")

    # D-2: items AFTER the aborting comparison on the same physical line do
    # not run (the whole line aborts) -- same contract as the parenthesized
    # form (PRINT (A$<5)) above, now exercised through the bare form.
    mm, out = run_prog_cap([
        (10, 'A$="HI"'),
        (20, 'PRINT A$<5:PRINT "AFTER"'),
    ])
    check('PRINT A$<5:PRINT "AFTER"  the trailing PRINT does not run',
          out == b"Type mismatch in 20\r\n", f"got {out!r}")

    # ------------------------------------------------------------------
    print("# --- S2 regression watch: plain PRINT items unchanged when NO "
          "relop follows (no re-parse; the S5 STRMAX-clamp lesson) ---")

    mm, out = run_prog_cap([
        (10, 'A$="HI"'),
        (20, "PRINT A$"),
    ])
    check('PRINT A$  (plain var, no relop) -> "HI"', out == b"HI\r\n", f"got {out!r}")

    mm, out = run_prog_cap([
        (10, 'PRINT "lit"'),
    ])
    check('PRINT "lit"  (plain literal, no relop) -> "lit"',
          out == b"lit\r\n", f"got {out!r}")

    mm, out = run_prog_cap([
        (10, 'PRINT "a"+"b"'),
    ])
    check('PRINT "a"+"b"  (literal concat, no relop) -> "ab"',
          out == b"ab\r\n", f"got {out!r}")

    mm, out = run_prog_cap([
        (10, 'A$="HELLO"'),
        (20, "PRINT LEFT$(A$,1)"),
    ])
    check('PRINT LEFT$(A$,1)  (plain function, no relop) -> "H"',
          out == b"H\r\n", f"got {out!r}")

    # multi-item PRINT: exercises the "print branch" stack balance across
    # exp_loop's continuation (';' join, no spacing) -- a stack leak in
    # exps_print/ems_print would corrupt this or crash the host Z80 core.
    mm, out = run_prog_cap([
        (10, 'A$="AB"'),
        (20, 'B$="CD"'),
        (30, 'PRINT A$;":";B$'),
    ])
    check('PRINT A$;":";B$  (multi-item, stack-balance regression) -> "AB:CD"',
          out == b"AB:CD\r\n", f"got {out!r}")

    # D-3: a comparison after a ';'-separated item is a FRESH PRINT item and
    # gets the same relop_peek treatment (each ;/,-separated item re-enters
    # exp_loop) -- also confirms the earlier item's own stack use didn't leak.
    mm, out = run_prog_cap([
        (10, 'A$="X"'),
        (20, 'B$="AB"'),
        (30, 'C$="ABC"'),
        (40, "PRINT A$;B$<C$"),
    ])
    check('PRINT A$;B$<C$  (comparison after ";" is a fresh item) -> "X-1 "',
          out == b"X-1 \r\n", f"got {out!r}")

    print()
    print("ALL PASS — string-compare S2 (comparator + type mismatch)" if not fails
          else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
