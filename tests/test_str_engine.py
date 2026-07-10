# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: string engine S3 — `+` concatenation spine (repack build only).

The string engine (basic/str-engine.asm + the concat-aware str_eval wrapper in
basic/strvar.asm) is assembled ONLY in the repack build (ROM_BASE < $4000), where the
reclaimed low region holds it and STRMAX widens to 64. So this test builds
basic/main-reloc.asm (ROM_BASE=$2812) and loads it at that base — the lean build has
no concat and would fail these cases by design.

Strategy mirrors test_expr / test_strvar: tokenise an ASCII string expression (so `+`
crunches to PLUS_TOKEN $F1 and literals pass through verbatim), then call the PUBLIC
`str_eval` and read the [len][bytes] descriptor STRPTR points at.

Oracle basis:
- Concatenation semantics (left-to-right join, combined length clamped) — public
  MSX-BASIC language reference; the clamp value STRMAX=64 and the fixed temp ring are
  zerobas own-design (docs/spec-basic-string-engine.md §3, §6 D-C; basic/PROVENANCE.md).
- str_eval contract: STRPTR -> [len][bytes], VALTYP=1, CF=1 on success (strvar.asm).
- Result of a concat lands in the STRTMP result ring (str-engine.asm str_alloc_temp);
  a single operand (no '+') is unchanged — STRPTR = STRSCR for a literal.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

ROM = "/tmp/zb_strengine.rom"
SYM = "/tmp/zb_strengine.sym"
RELOC_BASE = 0x2812

SRC     = 0xC000   # ASCII expression source
TOKBUF  = 0xC100   # crunched-token buffer
SETSRC  = 0xC300   # str_set_key source descriptor scratch


def build():
    src = os.path.join(ROOT, "basic", "main-reloc.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=RELOC_BASE)
    s = m.sym

    STRMAX = s["STRMAX"]
    STRPTR = s["STRPTR"]
    VALTYP = s["VALTYP"]
    STRSCR = s["STRSCR"]
    STRTMP = s["STRTMP"]
    STRNTMP = s["STRNTMP"]
    STRTMPSZ = s["STRTMPSZ"]
    STRTAB = s["STRTAB"]
    STRENTSZ = s["STRENTSZ"]
    STRSLOTS = s["STRSLOTS"]
    ring_end = STRTMP + STRNTMP * STRTMPSZ

    fails = 0

    def reset_strtab():
        for i in range(STRSLOTS):
            m.poke(STRTAB + i * STRENTSZ, 0)

    def set_var(name, value):
        """Store value under key (name,0) via str_set_key."""
        m.poke(SETSRC, bytes([len(value)]) + value)
        m.call("str_set_key", b=ord(name), c=0, de=SETSRC)

    def eval_expr(text):
        """Tokenise an ASCII string expression, call str_eval, return (cpu, desc)."""
        m.poke(SRC, text.encode("ascii") + b"\x00")
        m.mem[TOKBUF:TOKBUF + 96] = b"\x00" * 96
        m.call("tokenise", hl=SRC, de=TOKBUF)
        m.poke(VALTYP, 0)
        m.poke_w(STRPTR, 0)
        cpu = m.call("str_eval", hl=TOKBUF)
        ptr = m.mem[STRPTR] | (m.mem[STRPTR + 1] << 8)
        dlen = m.mem[ptr]
        dbytes = bytes(m.mem[ptr + 1: ptr + 1 + dlen])
        return cpu, ptr, dlen, dbytes

    def check(label, cpu, ptr, dlen, dbytes, want_bytes, want_ring=None):
        nonlocal fails
        ok = carry(cpu) and m.mem[VALTYP] == 1 and dbytes == want_bytes and dlen == len(want_bytes)
        if want_ring is True:
            ok = ok and (STRTMP <= ptr < ring_end)
        elif want_ring is False:
            ok = ok and (ptr == STRSCR)
        fails += not ok
        loc = "ring" if STRTMP <= ptr < ring_end else ("STRSCR" if ptr == STRSCR else f"{ptr:#06x}")
        print(f"{'PASS' if ok else 'FAIL'}  {label}: CF={int(carry(cpu))} "
              f"VALTYP={m.mem[VALTYP]} len={dlen} bytes={dbytes!r} @{loc}")

    print(f"# repack build: STRMAX={STRMAX}, ring {STRNTMP}x{STRTMPSZ} @ {STRTMP:#06x}")
    # STRMAX must be the widened repack value (D-C).
    ok_max = (STRMAX == 64)
    fails += not ok_max
    print(f"{'PASS' if ok_max else 'FAIL'}  STRMAX widened to 64 in the repack build")

    # 1) binary literal concat -> result in the ring
    check('"AB"+"CD"', *eval_expr('"AB"+"CD"'), b"ABCD", want_ring=True)

    # 2) three-operand literal concat (associativity / iterative accumulate)
    check('"A"+"B"+"C"', *eval_expr('"A"+"B"+"C"'), b"ABC", want_ring=True)

    # 3) THE spec case: variable concat A$+B$+C$
    reset_strtab()
    set_var("A", b"HE"); set_var("B", b"LL"); set_var("C", b"O")
    check('A$+B$+C$ (HE+LL+O)', *eval_expr("A$+B$+C$"), b"HELLO", want_ring=True)

    # 4) mixed variable + literal
    reset_strtab()
    set_var("A", b"HI")
    check('A$+"!"', *eval_expr('A$+"!"'), b"HI!", want_ring=True)

    # 5) single operand (no '+') is UNCHANGED: literal still lands in STRSCR
    check('"XY" (single operand)', *eval_expr('"XY"'), b"XY", want_ring=False)

    # 6) combined length clamps to STRMAX (own-design truncation)
    a40 = b"a" * 40
    b40 = b"b" * 40
    cpu, ptr, dlen, dbytes = eval_expr(f'"{a40.decode()}"+"{b40.decode()}"')
    want = (a40 + b40)[:STRMAX]
    check(f'40+40 chars clamps to {STRMAX}', cpu, ptr, dlen, dbytes, want, want_ring=True)

    # 7) empty operands
    check('""+"Z"', *eval_expr('""+"Z"'), b"Z", want_ring=True)
    check('"Z"+""', *eval_expr('"Z"+""'), b"Z", want_ring=True)

    # 8) long variable chain uses only ONE ring slot (A$ x 6, each "XX")
    reset_strtab()
    set_var("A", b"XX")
    check('A$+A$+A$+A$+A$+A$', *eval_expr("A$+A$+A$+A$+A$+A$"), b"XX" * 6, want_ring=True)

    print()
    print("ALL PASS — string engine S3 (+ concat)" if not fails
          else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
