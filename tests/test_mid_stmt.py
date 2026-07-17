# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: MID$ statement — MID$(A$,n[,m])=B$ (repack build only),
docs/spec-basic-mid-statement.md.

Exercises the in-RAM overwrite math (compute k = min(m|Lb, Lb, La-n+1); copy in
place; LEN(A$) invariant) directly, with no emulator: tokenise a full
`MID$(A$,n,m)="..."` statement, seed A$ in STRTAB, call ex_mid_stmt on the crunched
bytes, and read A$ back. The handler ends in `jp exec_stmt`, which returns at the
end-of-line $00 with no BIOS output — so the SUCCESS path is host-testable. The
range/type ERROR path routes through stmt_error -> print_string -> CHPUT (a BIOS
entry absent in the host), so it is covered by the live acceptance gate
(basic_probe_mid_stmt.py), not here.

Like test_str_fn/test_str_engine this builds basic/main-reloc.asm (ROM_BASE=$2812);
the lean 16 KB build has no string engine and no MID$ statement (the exec_stmt hook
is gated out, byte-identical) and would fail this by design.

Oracle basis: the MID$ statement token ($FF $83, same as the MID$ function) is a
black-box VG-8020 crunch capture (S2); the overwrite semantics (LEN(A$) invariant,
truncate-to-fit, m/Lb/avail min) are the public MSX-BASIC contract, confirmed
against the real VG-8020 in S2/S3. No disassembly.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = "/tmp/zb_midstmt.rom"
SYM = "/tmp/zb_midstmt.sym"
RELOC_BASE = 0x2812

SRC = 0xC000     # ASCII statement source
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
    # every string-heap op derives its array-region ceiling via ARYTAB (was
    # (PRGEND)+2). A fresh Machine zero-inits ALL RAM, so an unpoked PRGEND/
    # ARYTAB=0 makes that derivation land inside the SUB-ROM'S OWN CODE BYTES
    # (shuttled 0x8000+ RAM aside, ARYBASE=0 sits at the very start of the
    # bridged sub-ROM image) -- a stride-walk over $FF padding can spin
    # (near-)forever. Seed both to a safe placeholder RAM address (matching
    # tests/test_arrays.py's own convention) so any heap_alloc/strheap_gc
    # this statement triggers walks harmless (empty) RAM instead.
    m.poke_w(s["PRGEND"], 0x9000)
    m.poke(0x9000, b"\x00\x00")
    m.poke_w(s["ARYTAB"], 0x9002)
    m.poke(0x9002, b"\x00\x00")
    # Arrays slice-4a (docs/spec-basic-arrays-slice4a-string-heap.md §2/§5):
    # a repack-build string VALUE lives in the compacting heap; the STRTAB slot
    # holds a [len:1][ptr:2] descriptor. heap_reset seeds FRETOP (empty heap) +
    # TEMPTOP (empty temp stack) as a real cold boot does, so str_set_key's
    # heap_alloc has somewhere to put A$'s body.
    m.call("heap_reset")

    fails = 0

    def reset_strtab():
        # Arrays slice-4c (docs/spec-basic-arrays-slice4c-string-scalar-
        # unification.md §3d): string scalars are chain-resident now,
        # sharing [PRGEND+2, ARYTAB) with numeric scalars/arrays -- the
        # fixed STRTAB pool this helper used to zero is GONE. The
        # equivalent reset is re-anchoring ARYTAB to the scalar-region
        # base and rewriting the "no arrays" sentinel there (exactly what
        # vars_reset/ary_reset do; mirrors the identical poke in the
        # initial setup above).
        m.poke_w(s["ARYTAB"], 0x9002)
        m.poke(0x9002, b"\x00\x00")

    def set_var(name, value):
        # str_set_key source = a STABLE [len][ptr] descriptor (slice-4a §10):
        # sh_var_store follows ptr to copy the body into a fresh heap alloc.
        m.poke(BODY, value)
        m.poke(SETSRC, bytes([len(value)]))
        m.poke_w(SETSRC + 1, BODY)
        m.call("str_set_key", b=ord(name), c=0, de=SETSRC)

    def get_var(name):
        # str_get_key returns HL -> the slot's [len][ptr] descriptor; follow
        # ptr to the heap body (the value bytes are no longer inline).
        cpu = m.call("str_get_key", b=ord(name), c=0)
        addr = cpu.hl & 0xFFFF
        dlen = m.mem[addr]
        if dlen == 0:
            return b""
        bptr = m.mem[addr + 1] | (m.mem[addr + 2] << 8)
        return bytes(m.mem[bptr: bptr + dlen])

    def mid_stmt(stmt, avar, aval):
        """Seed A$=aval, tokenise `stmt`, run ex_mid_stmt, return A$'s new bytes."""
        reset_strtab()
        set_var(avar, aval)
        m.poke(SRC, stmt.encode("ascii") + b"\x00")
        m.mem[TOKBUF:TOKBUF + 192] = b"\x00" * 192
        m.call("tokenise", hl=SRC, de=TOKBUF)
        # ex_mid_stmt expects HL on the leading $FF (PEEK_PREFIX) token.
        m.call("ex_mid_stmt", hl=TOKBUF)
        return get_var(avar)

    def ck(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label} = {got!r} (want {want!r})")

    print("# --- MID$ statement: in-place overwrite, LEN(A$) invariant ---")
    ck('MID$(A$,2,3)="XYZ"',  mid_stmt('MID$(A$,2,3)="XYZ"',  "A", b"HELLO"), b"HXYZO")
    ck('MID$(A$,3)="XY"',     mid_stmt('MID$(A$,3)="XY"',     "A", b"HELLO"), b"HEXYO")
    ck('MID$(A$,1)="XY"',     mid_stmt('MID$(A$,1)="XY"',     "A", b"HELLO"), b"XYLLO")
    ck('MID$(A$,5,1)="Z"',    mid_stmt('MID$(A$,5,1)="Z"',    "A", b"HELLO"), b"HELLZ")

    print("# --- truncation: B$ / m clipped to the room left in A$ ---")
    ck('MID$(A$,4)="WXYZ"',   mid_stmt('MID$(A$,4)="WXYZ"',   "A", b"HELLO"), b"HELWX")
    ck('MID$(A$,4,10)="WXYZ"',mid_stmt('MID$(A$,4,10)="WXYZ"',"A", b"HELLO"), b"HELWX")
    ck('MID$(A$,1,2)="ABCD"', mid_stmt('MID$(A$,1,2)="ABCD"', "A", b"HELLO"), b"ABLLO")

    print("# --- degenerate: empty B$ / m=0 leave A$ unchanged ---")
    ck('MID$(A$,2)=""',       mid_stmt('MID$(A$,2)=""',       "A", b"HELLO"), b"HELLO")
    ck('MID$(A$,2,0)="XY"',   mid_stmt('MID$(A$,2,0)="XY"',   "A", b"HELLO"), b"HELLO")

    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(run())
