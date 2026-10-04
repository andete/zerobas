# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: string engine S3 — `+` concatenation spine (repack build only).

The string engine (basic/str-engine.asm + the concat-aware str_eval wrapper in
basic/strvar.asm) is assembled ONLY in the repack build (ROM_BASE < $4000), where the
reclaimed low region holds it and STRMAX widens to 255. So this test builds
basic/main-reloc.asm (ROM_BASE=$2812) and loads it at that base — the lean build has
no concat and would fail these cases by design.

Strategy mirrors test_expr / test_strvar: tokenise an ASCII string expression (so `+`
crunches to PLUS_TOKEN $F1 and literals pass through verbatim), then call the PUBLIC
`str_eval` and follow the [len:1][ptr:2] descriptor STRPTR points at to its heap body.

Oracle basis:
- Concatenation semantics (left-to-right join) — public MSX-BASIC language
  reference. 🔴 A COMBINED LENGTH OVER STRMAX=255 RAISES `String too long`
  (ERR 15), it does not truncate: this file asserted the truncation until
  2026-08-28 and the assertion was the divergence (D-STRLONG,
  docs/spec-basic-strlong.md; docs/spec-basic-string-engine.md §3).
- str_eval contract: STRPTR -> [len][ptr], VALTYP=1, CF=1 on success (strvar.asm).
- String home (arrays slice-4a, docs/spec-basic-arrays-slice4a-string-heap.md §3/§6/§7):
  the fixed STRTMP N=3 ring is retired. A CONCAT result is a temp-descriptor-stack
  entry ([TEMPPOOL,TEMPBASE)) owning a heap body; a single un-concatenated literal is
  a zero-copy RVDESC rvalue (STRPTR = RVDESC), never allocated a temp.
"""

import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

ROM = tp("zb_strengine.rom")
SYM = tp("zb_strengine.sym")
RELOC_BASE = 0x2765

SRC     = 0xC000   # ASCII expression source
TOKBUF  = 0xC100   # crunched-token buffer
SETSRC  = 0xC300   # str_set_key source descriptor scratch ([len][ptr])
BODY    = 0xC500   # scratch body the SETSRC descriptor points at (slice-4a heap)


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=RELOC_BASE)
    s = m.sym
    # Arrays slice-4a/4b (docs/spec-basic-arrays-slice4a-string-heap.md §2/§5/§6,
    # spec-basic-arrays-slice4b-scalar-reloc.md §2/Q3): the fixed STRTMP N=3 ring
    # is RETIRED. A computed string now lives in the compacting heap (bodies grow
    # down from FRETOP) and its descriptor [len:1][ptr:2] is either an RVDESC
    # (single un-concatenated literal/function rvalue), a var slot, or a
    # temp-descriptor-stack entry ([TEMPPOOL,TEMPBASE), where every CONCAT result
    # lands). heap_reset seeds FRETOP (empty heap) + TEMPTOP (empty temp stack) as
    # a real cold boot does; PRGEND/ARYTAB seed the array-region ceiling every
    # heap op derives (an unpoked ARYTAB=0 would send the stride-walk into the
    # sub-ROM's own code bytes and spin -- matching tests/test_arrays.py).
    m.poke_w(s["PRGEND"], 0x9000)
    m.poke(0x9000, b"\x00\x00")
    m.poke_w(s["ARYTAB"], 0x9002)
    m.poke(0x9002, b"\x00\x00")
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

    STRMAX = s["STRMAX"]        # 255 in the repack build (slice-4a widened 64->255)
    FPERR = s["FPERR"]          # D-STRLONG: the deferred-error cell str_concat_tail
    FPERR_STRLONG = s["FPERR_STRLONG"]      # arms when a fold exceeds STRMAX
    STRPTR = s["STRPTR"]
    VALTYP = s["VALTYP"]
    RVDESC = s["RVDESC"]        # the single-rvalue descriptor cell (non-concat literals)
    TEMPPOOL = s["TEMPPOOL"]    # temp-descriptor stack floor / current frontier top
    TEMPPOOL = s["TEMPPOOL"]    # temp-descriptor pool base (empty = TEMPPT, which grows UP)
    TEMPBASE = s["TEMPBASE"]    # one past the last slot
    TEMPPT = s["TEMPPT"]

    fails = 0

    def in_temp(addr):
        """A concat result's descriptor is a temp-descriptor-stack entry."""
        return TEMPPOOL <= addr < TEMPBASE

    def read_val(addr):
        """Read a [len:1][ptr:2] descriptor -> the heap body bytes it points at."""
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

    def set_var(name, value):
        """Store value under key (name,0) via str_set_key. The source is a
        STABLE [len][ptr] descriptor (slice-4a §10): sh_var_store follows ptr
        to copy the body into a fresh heap allocation."""
        m.poke(BODY, value)
        m.poke(SETSRC, bytes([len(value)]))
        m.poke_w(SETSRC + 1, BODY)
        m.call("str_set_key", b=ord(name), c=0, de=SETSRC)

    def eval_expr(text):
        """Tokenise an ASCII string expression, call str_eval, return
        (cpu, descaddr, len, bytes). Resets the temp stack first, mirroring
        exec_stmt's per-statement boundary (str_eval bypasses it)."""
        m.poke(SRC, text.encode("ascii") + b"\x00")
        m.mem[TOKBUF:TOKBUF + 96] = b"\x00" * 96
        m.call("tokenise", hl=SRC, de=TOKBUF)
        m.poke_w(TEMPPT, TEMPPOOL)
        m.poke(VALTYP, 0)
        m.poke_w(STRPTR, 0)
        m.poke(s["FPERR"], 0)       # D-STRLONG: exec_stmt clears the pending-error
                                    # cell at every statement boundary and str_eval
                                    # bypasses it, so a case that ARMS FPERR would
                                    # otherwise leak into the next case's reading
        cpu = m.call("str_eval", hl=TOKBUF)
        ptr = m.mem[STRPTR] | (m.mem[STRPTR + 1] << 8)
        dlen, dbytes = read_val(ptr)
        return cpu, ptr, dlen, dbytes

    def check(label, cpu, ptr, dlen, dbytes, want_bytes, want_temp=None):
        nonlocal fails
        ok = carry(cpu) and m.mem[VALTYP] == 1 and dbytes == want_bytes and dlen == len(want_bytes)
        if want_temp is True:
            ok = ok and in_temp(ptr)              # concat result -> temp stack
        elif want_temp is False:
            ok = ok and (ptr == RVDESC)           # single literal rvalue -> RVDESC
        fails += not ok
        loc = "temp" if in_temp(ptr) else ("RVDESC" if ptr == RVDESC else f"{ptr:#06x}")
        print(f"{'PASS' if ok else 'FAIL'}  {label}: CF={int(carry(cpu))} "
              f"VALTYP={m.mem[VALTYP]} len={dlen} bytes={dbytes!r} @{loc}")

    print(f"# repack build: STRMAX={STRMAX}, temp stack [{TEMPPOOL:#06x},{TEMPBASE:#06x})")
    # STRMAX must be the widened repack value (slice-4a: 64 -> 255).
    ok_max = (STRMAX == 255)
    fails += not ok_max
    print(f"{'PASS' if ok_max else 'FAIL'}  STRMAX widened to 255 in the repack build")

    # 1) binary literal concat -> result on the temp stack
    check('"AB"+"CD"', *eval_expr('"AB"+"CD"'), b"ABCD", want_temp=True)

    # 2) three-operand literal concat (associativity / iterative accumulate)
    check('"A"+"B"+"C"', *eval_expr('"A"+"B"+"C"'), b"ABC", want_temp=True)

    # 3) THE spec case: variable concat A$+B$+C$
    reset_strtab()
    set_var("A", b"HE"); set_var("B", b"LL"); set_var("C", b"O")
    check('A$+B$+C$ (HE+LL+O)', *eval_expr("A$+B$+C$"), b"HELLO", want_temp=True)

    # 4) mixed variable + literal
    reset_strtab()
    set_var("A", b"HI")
    check('A$+"!"', *eval_expr('A$+"!"'), b"HI!", want_temp=True)

    # 5) single operand (no '+') is UNCHANGED: a bare literal is a zero-copy
    #    RVDESC rvalue (never allocated a temp), not a temp-stack result.
    check('"XY" (single operand)', *eval_expr('"XY"'), b"XY", want_temp=False)

    # 6) 🔴 A COMBINED LENGTH OVER STRMAX RAISES; IT DOES NOT CLAMP (D-STRLONG,
    #    docs/spec-basic-strlong.md). Until 2026-08-28 this case asserted
    #    `200+200 chars clamps to 255` and PASSED -- the gate encoded the
    #    divergence. `X$=STRING$(200,"A") : PRINT LEN(X$+X$)` is
    #    `String too long` on both the VG-8020 and the CF-3300, so sh_append
    #    now answers the carry out of `add a,c` with SH_ERR=3 and
    #    str_concat_tail defers it as FPERR_STRLONG.
    #    What str_eval returns is UNCHANGED in shape: CF=1 (a string operand WAS
    #    recognised -- only its value errored), VALTYP=1, and STRPTR -> R, the
    #    partial accumulator, which is still a valid temp because the length is
    #    tested BEFORE any allocation. R therefore holds operand 1 untouched.
    reset_strtab()
    a200 = b"a" * 200
    set_var("A", a200)
    cpu, ptr, dlen, dbytes = eval_expr("A$+A$")
    got_fperr = m.mem[FPERR]
    ok = (carry(cpu) and m.mem[VALTYP] == 1 and in_temp(ptr)
          and dbytes == a200 and got_fperr == FPERR_STRLONG)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  200+200 raises String too long (no clamp): "
          f"CF={int(carry(cpu))} VALTYP={m.mem[VALTYP]} len={dlen} "
          f"FPERR={got_fperr} (want {FPERR_STRLONG}) R-intact={dbytes == a200}")

    # 6b) 🟢 THE GREEN CONTROL ON THE SAME APPARATUS. Exactly STRMAX bytes is
    #    LEGAL and must stay legal -- without this row, a fix that raised one
    #    byte early would score perfect on case 6 and every other case here.
    #    (The emulator-side twin is probe row `e.255`, and knife K-SL4 is what
    #    proves the pair is load-bearing rather than decorative.)
    reset_strtab()
    a200 = b"a" * 200
    b55 = b"b" * 55
    set_var("A", a200); set_var("B", b55)
    cpu, ptr, dlen, dbytes = eval_expr("A$+B$")
    ok = (carry(cpu) and m.mem[VALTYP] == 1 and in_temp(ptr)
          and dbytes == a200 + b55 and m.mem[FPERR] == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  exactly {STRMAX} chars is LEGAL: "
          f"CF={int(carry(cpu))} len={dlen} FPERR={m.mem[FPERR]} (want 0)")

    # 7) empty operands
    check('""+"Z"', *eval_expr('""+"Z"'), b"Z", want_temp=True)
    check('"Z"+""', *eval_expr('"Z"+""'), b"Z", want_temp=True)

    # 8) long variable chain: the whole 6-operand concat still yields a single
    #    string result (A$ x 6, each "XX") -- the temp-descriptor stack absorbs
    #    the operands, the accumulate lands as one temp (no N=3 ring truncation).
    reset_strtab()
    set_var("A", b"XX")
    check('A$+A$+A$+A$+A$+A$', *eval_expr("A$+A$+A$+A$+A$+A$"), b"XX" * 6, want_temp=True)

    print()
    print("ALL PASS — string engine S3 (+ concat)" if not fails
          else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
