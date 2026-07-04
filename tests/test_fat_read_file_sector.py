# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM fat_read_file_sector data-sector math + EOF, no emulator.

fat_read_file_sector maps the open file's (cluster, clussec) iterator to an
absolute logical sector and reads it:

    sector = FAT_FIRSTDATA + (FAT_CURCLUS - 2) * FAT_SECPERCLUS + FAT_CLUSSEC

It advances to the next cluster when the in-cluster sector index reaches
FAT_SECPERCLUS, and returns Cy=1 (end-of-file) when the current cluster is < 2 or
>= $0FF8 (end-of-chain). We MOCK read_sector (to capture the requested absolute
sector) and fat_advance (to isolate the address math from the chain walk, which
test_fat_next_cluster already covers); the arithmetic runs for real.

Checks: the absolute-sector formula (mid-cluster), the cluster-advance path (a
new cluster + clussec reset feeds the formula), clussec post-increment, and both
EOF guards.

Clean-room: our own routine (fat.asm/kernel.asm), public FAT §3.3 data-sector
math — no stock disassembly.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

ROM = "/tmp/zb_frs_ut.rom"
SYM = "/tmp/zb_frs_ut.sym"

FIRSTDATA = 14
SECPERCLUS = 2


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def new_machine():
    m = Machine(ROM, SYM)
    m.poke(m.addr("FAT_SECPERCLUS"), SECPERCLUS)
    m.poke_w(m.addr("FAT_FIRSTDATA"), FIRSTDATA)
    return m


def set_iter(m, cluster, clussec):
    m.poke_w(m.addr("FAT_CURCLUS"), cluster)
    m.poke(m.addr("FAT_CLUSSEC"), clussec)


def run():
    build()
    fails = 0
    captured = []

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    def read_sector(mm):
        captured.append(mm.cpu.de)              # absolute sector requested
        mm.cpu.f &= ~0x01

    # --- case 1: mid-cluster sector math --------------------------------------
    # cluster 5, clussec 1 -> 14 + (5-2)*2 + 1 = 21
    m = new_machine()
    m.trap("read_sector", read_sector)
    set_iter(m, 5, 1)
    captured.clear()
    cpu = m.call("fat_read_file_sector")
    check(not carry(cpu), "read_file_sector(cluster 5, clussec 1) -> Cy=0")
    check(captured == [21], f"  requested sector {captured} (want [21])")
    check(m.mem[m.addr("FAT_CLUSSEC")] == 2, "  FAT_CLUSSEC post-incremented 1 -> 2")

    # --- case 2: cluster-advance path -----------------------------------------
    # clussec == secPerClus triggers fat_advance; mock it to move to cluster 9,
    # clussec 0 -> 14 + (9-2)*2 + 0 = 28
    m = new_machine()
    m.trap("read_sector", read_sector)

    def mock_advance(mm):
        mm.poke_w(mm.addr("FAT_CURCLUS"), 9)
        mm.poke(mm.addr("FAT_CLUSSEC"), 0)

    m.trap("fat_advance", mock_advance)
    set_iter(m, 5, SECPERCLUS)                   # clussec == secPerClus -> advance
    captured.clear()
    cpu = m.call("fat_read_file_sector")
    check(not carry(cpu), "read_file_sector(clussec == secPerClus) -> Cy=0 (advanced)")
    check(captured == [28], f"  requested sector {captured} (want [28], new cluster 9)")
    check(m.mem[m.addr("FAT_CLUSSEC")] == 1, "  FAT_CLUSSEC 0 -> 1 after advance")

    # --- case 2b: exact-multiple cluster-boundary EOF -------------------------
    # A file whose size is an EXACT multiple of the cluster size: its final
    # cluster is FULL (all secPerClus sectors read Cy=0), then the caller loops
    # once more, clussec == secPerClus triggers fat_advance, and fat_advance
    # lands on the end-of-chain marker. The routine must then EOF *and read
    # nothing* -- never compute a sector for the $FFF cluster (the "one cluster
    # too many" read an EOF off-by-one would cause). This is the routine-level
    # twin of the Class-1 artifact-oracle fact (disk_fat_eof_oracle.py).
    m = new_machine()
    m.trap("read_sector", read_sector)

    def advance_to_eoc(mm):
        mm.poke_w(mm.addr("FAT_CURCLUS"), 0x0FFF)   # fat_advance hit end-of-chain
        mm.poke(mm.addr("FAT_CLUSSEC"), 0)

    m.trap("fat_advance", advance_to_eoc)
    set_iter(m, 7, SECPERCLUS)                       # last full cluster exhausted
    captured.clear()
    cpu = m.call("fat_read_file_sector")
    check(carry(cpu), "read_file_sector(advance -> end-of-chain) -> Cy=1 (EOF)")
    check(captured == [], f"  read NOTHING past the last full cluster (got {captured})")

    # --- case 3: EOF guards ---------------------------------------------------
    m = new_machine()
    m.trap("read_sector", read_sector)
    set_iter(m, 1, 0)                            # cluster < 2
    check(carry(m.call("fat_read_file_sector")), "read_file_sector(cluster 1) -> Cy=1 (EOF)")

    m = new_machine()
    m.trap("read_sector", read_sector)
    set_iter(m, 0x0FF8, 0)                       # end-of-chain marker
    check(carry(m.call("fat_read_file_sector")), "read_file_sector(cluster 0x0FF8) -> Cy=1 (EOF)")

    print()
    print("ALL PASS — fat_read_file_sector address math + advance + EOF"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
