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
SETSRC = 0xC300  # str_set_key source descriptor scratch


def build():
    src = os.path.join(ROOT, "basic", "main-reloc.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=RELOC_BASE)
    s = m.sym
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

    def get_var(name):
        cpu = m.call("str_get_key", b=ord(name), c=0)
        ptr = cpu.hl & 0xFFFF
        dlen = m.mem[ptr]
        return bytes(m.mem[ptr + 1: ptr + 1 + dlen])

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
