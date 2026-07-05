# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: M31 k_47B2 faithful Random Block Read ($27 RDBLK), no emulator.

tier2-m31-rdblk-randrecord-spec.md: k_47B2 (the kernel's page-1 $27 handler
body, disk/kernel.asm) used to be a "stream-from-0" simplification -- it
ignored the FCB's random-record field (FCB+33..35) and the requested count,
always reading the whole file from record 0 to EOF. M31 rewrites it into a
faithful Random Block Read: position to record RR, transfer up to HL records
of the FCB's record size (FCB+14..15, 0 -> 128 default), zero-pad a final
partial record, report the true delivered count, and advance RR by the count
delivered (unchanged at/past EOF, since HL=0 there).

This test drives the REAL relocated body (k47b2_body, reached via the k_47B2
veneer's `jp` -- called directly by symbol here, exactly as test_wrblk_cursor.py
and test_wrblk_body_e2e.py call their routines under test by label) against a
synthetic FAT12 file. k47b2_body itself calls fat_open (re-priming the
iterator from FAT_FIRSTCLUS), so the test seeds FAT_FIRSTCLUS/FAT_FILESIZE
directly -- exactly the state a preceding kernel FOPEN would have left, per
k_47B2's own long-standing contract note (kernel.asm).

Cases mirror the spec's §1-Q3 table:
  (a) mid-file             RR=1 cnt=1  -> A=0 HL=1 RR=2,   record 1 delivered
  (b) EOF mid-transfer     RR=1 cnt=4  -> A=1 HL=2 RR=3,   records 1,2
  (b') partial tail        RR=1 cnt=4, file ends mid-record -> zero-padded final record
  (c) at EOF               RR=3 cnt=1  -> A=1 HL=0 RR=3 (unchanged), DTA untouched
  (c') past EOF            RR=10 cnt=1 -> A=1 HL=0 RR=10 (unchanged)
Plus RS != 128 (including RS=1, the boot loaders' record size) and the
FCB+33..35 write-back (RR := entry-RR + HL) for every row.

Clean-room: our own routine (kernel.asm), our own synthetic disk image, the
published RANDOM BLOCK READ contract (map.grauw.nl _RDBLK) + this project's own
black-box behavioural characterisation -- no stock disassembly. See
disk/docs/tier2-m31-rdblk-randrecord-spec.md.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from test_wrblk_body_e2e import Disk, build, n83  # noqa: E402
from msxtest import Machine  # noqa: E402

ROM = "/tmp/zb_wrblk_e2e_ut.rom"     # same build as test_wrblk_body_e2e.py (shared)
SYM = "/tmp/zb_wrblk_e2e_ut.sym"

FCB = 0xDA40
DTA = 0xC000


def new_machine():
    return Machine(ROM, SYM)


def make_file(m, name, data, first_cluster=5, secperclus_bytes=512):
    """Build a synthetic on-disk file holding exactly `data` (bytes), install
    the read/write traps, mount the (synthetic) BPB for real via fat_mount
    (seeds FAT_SECPERCLUS/FAT_FIRSTDATA/etc. -- k47b2_body's rdblk_getbyte ->
    fat_read_file_sector chain needs these, normally seeded once at boot), and
    seed FAT_FIRSTCLUS/FAT_FILESIZE as a preceding kernel FOPEN/fat_find would
    have (k47b2_body's own contract -- it re-primes via fat_open only, it does
    not search for the file itself; matches k_47B2's long-standing design)."""
    nclus = max(1, (len(data) + secperclus_bytes - 1) // secperclus_bytes)
    chain_links = []
    for i in range(nclus - 1):
        chain_links.append((first_cluster + i, first_cluster + i + 1))
    chain_links.append((first_cluster + nclus - 1, 0xFFF))
    disk = Disk(name, first_cluster=first_cluster, size=len(data), chain_links=chain_links)
    # lay the real file bytes into the data area (Disk() pre-fills 0xAA "garbage")
    base = (first_cluster - 2) * secperclus_bytes
    disk.data[base:base + len(data)] = data
    disk.install(m)
    cpu = m.call("fat_mount")
    assert not (cpu.f & 0x01), "fat_mount failed against the synthetic BPB"
    m.poke_w(m.addr("FAT_FIRSTCLUS"), first_cluster)
    m.poke(m.addr("FAT_FILESIZE"), struct.pack("<I", len(data)))
    return disk


def setup_fcb(m, name, rs, rr):
    m.poke(FCB, bytes(37))
    m.poke(FCB + 1, n83(name))
    m.poke_w(FCB + 14, rs)                      # FCB+14..15: record size
    m.poke(FCB + 33, struct.pack("<I", rr)[:3])  # FCB+33..35: random-record (24-bit)
    m.poke_w(m.addr("DOS_DTAPTR"), DTA)


def call_rdblk(m, count):
    m.poke(DTA, bytes([0xEE] * 1024))            # DTA canary (detect stray/short writes)
    return m.call("k47b2_body", de=FCB, hl=count)


def rr_of(m):
    r0, r1, r2 = m.peek(FCB + 33, 3)
    return r0 | (r1 << 8) | (r2 << 16)


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    RS = 128
    file_384 = bytes(range(256)) + bytes(range(128))  # 384 distinct-per-record bytes

    # === (a) mid-file: RR=1, cnt=1, 384B file (3 records of 128) -> A=0 HL=1 =====
    m = new_machine()
    make_file(m, "DATA.BIN", file_384)
    setup_fcb(m, "DATA.BIN", rs=RS, rr=1)
    cpu = call_rdblk(m, 1)
    check(cpu.a == 0, f"(a) mid-file: A={cpu.a} (want 0)")
    check((cpu.hl & 0xFFFF) == 1, f"  HL={cpu.hl & 0xFFFF} (want 1)")
    check((cpu.bc & 0xFFFF) == 1, f"  BC={cpu.bc & 0xFFFF} (want 1, BC==HL)")
    got = m.peek(DTA, RS)
    check(got == file_384[128:256], "  record 1's 128 bytes landed at DTA (not record 0)")
    check(m.peek(DTA + RS, 1) == b"\xEE", "  nothing written past the one requested record")
    check(rr_of(m) == 2, f"  RR advanced to {rr_of(m)} (want 2 = entry-RR 1 + HL 1)")

    # === (b) EOF mid-transfer: RR=1, cnt=4, 384B file -> A=1 HL=2 (records 1,2) ==
    m = new_machine()
    make_file(m, "DATA.BIN", file_384)
    setup_fcb(m, "DATA.BIN", rs=RS, rr=1)
    cpu = call_rdblk(m, 4)
    check(cpu.a == 1, f"(b) EOF mid-transfer: A={cpu.a} (want 1)")
    check((cpu.hl & 0xFFFF) == 2, f"  HL={cpu.hl & 0xFFFF} (want 2)")
    check((cpu.bc & 0xFFFF) == 2, f"  BC={cpu.bc & 0xFFFF} (want 2, BC==HL)")
    check(m.peek(DTA, RS) == file_384[128:256], "  record 1 landed correctly")
    check(m.peek(DTA + RS, RS) == file_384[256:384], "  record 2 landed correctly")
    check(rr_of(m) == 3, f"  RR advanced to {rr_of(m)} (want 3 = entry-RR 1 + HL 2)")

    # === (b') partial tail: RR=1, cnt=4, 300B file -> record 2 zero-padded ======
    file_300 = bytes(range(256)) + bytes(range(44))   # 300 bytes: rec0=128, rec1=128, rec2=44
    m = new_machine()
    make_file(m, "DATA.BIN", file_300)
    setup_fcb(m, "DATA.BIN", rs=RS, rr=1)
    cpu = call_rdblk(m, 4)
    check(cpu.a == 1, f"(b') partial tail: A={cpu.a} (want 1)")
    check((cpu.hl & 0xFFFF) == 2, f"  HL={cpu.hl & 0xFFFF} (want 2, the partial record COUNTS)")
    rec2 = m.peek(DTA + RS, RS)
    want_rec2 = file_300[256:300] + bytes(RS - 44)
    check(rec2 == want_rec2, "  record 2 (partial, 44 real bytes) zero-padded to RS=128")
    check(rr_of(m) == 3, f"  RR advanced to {rr_of(m)} (want 3 = entry-RR 1 + HL 2)")

    # === (c) at EOF: RR=3, cnt=1, 384B file (exactly 3 records) -> A=1 HL=0 =====
    m = new_machine()
    make_file(m, "DATA.BIN", file_384)
    setup_fcb(m, "DATA.BIN", rs=RS, rr=3)
    cpu = call_rdblk(m, 1)
    check(cpu.a == 1, f"(c) at EOF: A={cpu.a} (want 1)")
    check((cpu.hl & 0xFFFF) == 0, f"  HL={cpu.hl & 0xFFFF} (want 0)")
    check((cpu.bc & 0xFFFF) == 0, f"  BC={cpu.bc & 0xFFFF} (want 0, BC==HL)")
    check(m.peek(DTA, 1) == b"\xEE", "  DTA untouched (nothing delivered)")
    check(rr_of(m) == 3, f"  RR unchanged at {rr_of(m)} (want 3, += HL 0)")

    # === (c') past EOF: RR=10, cnt=1, 384B file -> A=1 HL=0, RR unchanged ========
    m = new_machine()
    make_file(m, "DATA.BIN", file_384)
    setup_fcb(m, "DATA.BIN", rs=RS, rr=10)
    cpu = call_rdblk(m, 1)
    check(cpu.a == 1, f"(c') past EOF: A={cpu.a} (want 1)")
    check((cpu.hl & 0xFFFF) == 0, f"  HL={cpu.hl & 0xFFFF} (want 0)")
    check(m.peek(DTA, 1) == b"\xEE", "  DTA untouched (nothing delivered)")
    check(rr_of(m) == 10, f"  RR unchanged at {rr_of(m)} (want 10, += HL 0)")

    # === IX/IY/$F306 unified-return contract (checked once; same path every row) =
    m = new_machine()
    make_file(m, "DATA.BIN", file_384)
    setup_fcb(m, "DATA.BIN", rs=RS, rr=0)
    m.poke(0xF306, 0xFF)                        # dirty the dispatcher flag first
    cpu = call_rdblk(m, 1)
    check((cpu.ix & 0xFFFF) == m.addr("DRVA_DPB"), f"  IX={cpu.ix & 0xFFFF:04X} (want DRVA_DPB)")
    check((cpu.iy & 0xFFFF) == FCB, f"  IY={cpu.iy & 0xFFFF:04X} (want entry FCB ptr {FCB:04X})")
    check(m.peek(0xF306, 1) == b"\x00", "  $F306 cleared (M20 dispatcher-flag rule)")

    # === RS != 128, RS=1 (the boot loaders' record size) =========================
    # RS=1: each "record" is one byte; RR positions to a byte offset directly.
    file_10 = bytes(range(10))
    m = new_machine()
    make_file(m, "DATA.BIN", file_10)
    setup_fcb(m, "DATA.BIN", rs=1, rr=3)
    cpu = call_rdblk(m, 2)
    check(cpu.a == 0, f"RS=1 mid-file: A={cpu.a} (want 0)")
    check((cpu.hl & 0xFFFF) == 2, f"  HL={cpu.hl & 0xFFFF} (want 2)")
    check(m.peek(DTA, 2) == bytes([3, 4]), "  bytes 3,4 delivered (RR=3, RS=1)")
    check(rr_of(m) == 5, f"  RR advanced to {rr_of(m)} (want 5 = 3+2)")

    # RS=1, boot-instantiation shape: RR=0, huge HL request -> runs to EOF, A=1,
    # HL=BC=filesize (§3.2 "boot instantiation check").
    m = new_machine()
    make_file(m, "DATA.BIN", file_10)
    setup_fcb(m, "DATA.BIN", rs=1, rr=0)
    cpu = call_rdblk(m, 0x7FFF)
    check(cpu.a == 1, f"RS=1 boot-shape (huge HL): A={cpu.a} (want 1, EOF)")
    check((cpu.hl & 0xFFFF) == 10, f"  HL={cpu.hl & 0xFFFF} (want 10 = filesize)")
    check((cpu.bc & 0xFFFF) == 10, f"  BC={cpu.bc & 0xFFFF} (want 10, BC==HL)")
    check(m.peek(DTA, 10) == file_10, "  the whole file landed at DTA in order")
    check(rr_of(m) == 10, f"  RR advanced to {rr_of(m)} (want 10, harmless per §3.2)")

    # RS=0 -> defaults to 128 (RECSIZE), same as bdos_rdblk's own normalisation.
    m = new_machine()
    make_file(m, "DATA.BIN", file_384)
    setup_fcb(m, "DATA.BIN", rs=0, rr=1)
    cpu = call_rdblk(m, 1)
    check(cpu.a == 0, f"RS=0 (defaults to 128): A={cpu.a} (want 0)")
    check(m.peek(DTA, 128) == file_384[128:256], "  record 1 (128B) delivered under the RS=0->128 default")

    # RS=64 (a non-128, non-1 record size; exercises the general RS-honoring path)
    RS64 = 64
    file_192 = bytes(range(192))   # 3 records of 64
    m = new_machine()
    make_file(m, "DATA.BIN", file_192)
    setup_fcb(m, "DATA.BIN", rs=RS64, rr=2)
    cpu = call_rdblk(m, 5)
    check(cpu.a == 1, f"RS=64 EOF mid-transfer: A={cpu.a} (want 1)")
    check((cpu.hl & 0xFFFF) == 1, f"  HL={cpu.hl & 0xFFFF} (want 1, only record 2 exists)")
    check(m.peek(DTA, RS64) == file_192[128:192], "  record 2 (last, exact multiple, RS=64) delivered")
    check(rr_of(m) == 3, f"  RR advanced to {rr_of(m)} (want 3 = 2+1)")

    print()
    print("ALL PASS — M31 k_47B2 faithful Random Block Read"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
