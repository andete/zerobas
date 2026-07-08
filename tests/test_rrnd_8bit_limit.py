# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: RDRND/WRRND ($21/$22) DOCUMENTED 8-bit-record / fixed-128-byte
boundary (option-closure Item 5, sibling; Q5.2 decided: document-and-gate, do
NOT widen), no emulator.

diskbasic-option-surface.md §1.3: rrnd_position (kernel.asm) reads only the FCB
random-record low byte r0 (+33), ignoring r1/r2 (+34/+35), and hardwires a
128-byte record stride (`and 3` record-in-sector + `srl a;srl a` sector = r0>>2),
ignoring the FCB record-size field (+14..15). This is a signed-off narrowing --
128-byte records addressing up to a 32640-byte file are the MSX-DOS-1 floppy
norm, and widening is unverified surface. The risk this gate guards against is
NOT the limit itself but a SILENT DRIFT of it: a future half-widening that reads
r1 but not r2, or half-honours +14/15, would random-access the wrong location
without any test noticing. So this is a NEGATIVE-BOUND assertion -- it pins that
r1/r2 and +14/15 are FULLY ignored (the code stays exactly at the documented
boundary), by proving that a read with r1/r2 set nonzero AND a non-128 record
size still delivers record r0 at a 128-byte stride.

Drives the REAL canonical body (rdrnd_body, reached by label) against a
synthetic FAT12 file, reusing test_wrblk_body_e2e.py's Disk harness (same
technique as test_rdblk_randrecord.py).

Clean-room: our own routine, our own synthetic disk, the published RDRND
contract + CP/M FCB layout + this project's own signed-off scope note -- no
stock disassembly.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from test_rdblk_randrecord import make_file, new_machine  # noqa: E402  (shared harness)
from test_wrblk_body_e2e import build, n83  # noqa: E402

FCB = 0xDA40
DTA = 0xC000
RECSIZE = 128


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    # 8 records (0..7), each 128 bytes filled with its own distinct marker byte
    # (0x10 + record index), one 1024-byte file.
    data = b"".join(bytes([0x10 + i]) * RECSIZE for i in range(8))

    # --- negative bound: r1/r2 nonzero + record size != 128 are all IGNORED ----
    # If r1/r2 were honoured, the target would be record 5 + 7*256 + 9*65536 --
    # far past EOF (would return A=$01, no data). If +14/15 (=200) were honoured,
    # the seek stride would be wrong and a different record would come back. So a
    # correctly-bounded read delivers exactly record 5 (marker 0x15) at a 128-byte
    # stride, and CR (+32) := r0 = 5.
    m = new_machine()
    make_file(m, "REC8.DAT", data)
    m.poke(FCB, bytes(37))
    m.poke(FCB + 1, n83("REC8.DAT"))
    m.poke_w(FCB + 14, 200)                       # record size 200 -- must be IGNORED
    m.poke(FCB + 33, bytes([5, 7, 9]))            # r0=5, r1=7, r2=9 -- r1/r2 must be IGNORED
    m.poke_w(m.addr("DOS_DTAPTR"), DTA)
    m.poke(DTA, bytes([0xEE] * 256))              # canary

    cpu = m.call("rdrnd_body", de=FCB)
    delivered = m.peek(DTA, RECSIZE)
    cr = m.peek(FCB + 32)[0]
    check(cpu.a == 0, f"r0=5,r1=7,r2=9,rs=200: A={cpu.a} (want 0 -- record 5 IS within EOF)")
    check(delivered == bytes([0x15]) * RECSIZE,
          f"delivered record marker = {delivered[0]:#04x} (want 0x15 = record 5; r1/r2 + rs IGNORED)")
    check(m.peek(DTA + RECSIZE, 1)[0] == 0xEE, "stride = 128 (byte 128 still the 0xEE canary, not a 200-byte read)")
    check(cr == 5, f"CR (+32) := r0 = {cr} (want 5)")

    # --- positive control: same r0 with r1/r2 = 0 delivers the SAME record ------
    # (proves the negative-bound result above is r0-positioning, not a fluke.)
    m2 = new_machine()
    make_file(m2, "REC8.DAT", data)
    m2.poke(FCB, bytes(37))
    m2.poke(FCB + 1, n83("REC8.DAT"))
    m2.poke_w(FCB + 14, 0)                         # record size 0 -> default 128
    m2.poke(FCB + 33, bytes([5, 0, 0]))
    m2.poke_w(m2.addr("DOS_DTAPTR"), DTA)
    m2.poke(DTA, bytes([0xEE] * 256))
    cpu2 = m2.call("rdrnd_body", de=FCB)
    delivered2 = m2.peek(DTA, RECSIZE)
    check(cpu2.a == 0 and delivered2 == bytes([0x15]) * RECSIZE,
          f"control r0=5,r1=r2=0: A={cpu2.a} marker={delivered2[0]:#04x} (want A=0, 0x15 -- same record)")

    print(f"\n{'ALL PASSED' if not fails else str(fails) + ' FAILED'}")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
