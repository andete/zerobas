# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM fat_alloc_cluster (FAT12 free-cluster scan), no emulator.

fat_alloc_cluster linearly scans the FAT from cluster 2 for the first $000 (free)
entry, claims it by writing EOC ($FFF) into every FAT copy, and returns it in HL
(Cy=0); Cy=1 on disk-full. Dependencies mocked against a synthetic FAT image:
fat_total_clusters (bounds the scan), read_sector (serves FAT sectors), and
write_sector (persists + records the EOC claim). The scan + claim run for real.

Checks: the first FREE cluster is chosen (not an earlier used one); the claim
writes EOC so the cluster reads back as end-of-chain via the verified reader
fat_next_cluster; and a fully-used FAT returns disk-full (Cy=1).

Clean-room: our own routine (fat.asm), our own FAT image, public Microsoft FAT
spec §3.2 ($000 = free, $FF8-$FFF = end-of-chain) — no stock disassembly.
"""

import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

# The image under test is loaded at its ORG. Named here rather than
# defaulted: msxtest.Machine's old default was $4000, the retired lean
# cart's org, so a BASIC test that omitted it silently tested the lean
# build (docs/spec-lean-retire-s3-gates.md §5, F-U).
DISK_BASE = 0x4000

ROM = "/tmp/zb_fatalloc_ut.rom"
SYM = "/tmp/zb_fatalloc_ut.sym"

FATSTART, SECSIZE, FAT_SECTORS = 1, 512, 3
NUMFATS, SECPERFAT = 2, 3
TOTAL = 20                       # valid data clusters are 2..19
EOC = 0xFFF


def put_fat12(fat, cluster, value):
    off = cluster + (cluster >> 1)
    if cluster & 1:
        fat[off] = (fat[off] & 0x0F) | ((value << 4) & 0xF0)
        fat[off + 1] = (value >> 4) & 0xFF
    else:
        fat[off] = value & 0xFF
        fat[off + 1] = (fat[off + 1] & 0xF0) | ((value >> 8) & 0x0F)


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def make_machine(used_clusters):
    """Fresh machine with a FAT image whose `used_clusters` are marked EOC."""
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    fat = bytearray(FAT_SECTORS * SECSIZE)
    for c in used_clusters:
        put_fat12(fat, c, EOC)

    def read_sector(mm):
        base = (mm.cpu.de - FATSTART) * SECSIZE
        chunk = bytes(fat[base:base + SECSIZE]) if 0 <= base < len(fat) else b""
        mm.poke(mm.cpu.hl, chunk.ljust(SECSIZE, b"\x00"))
        mm.cpu.f &= ~0x01

    def write_sector(mm):
        base = (mm.cpu.de - FATSTART) * SECSIZE
        if 0 <= base < len(fat):
            fat[base:base + SECSIZE] = bytes(mm.peek(mm.cpu.hl, SECSIZE))
        mm.cpu.f &= ~0x01

    m.trap("read_sector", read_sector)
    m.trap("write_sector", write_sector)
    m.trap("fat_total_clusters", lambda mm: setattr(mm.cpu, "de", TOTAL))
    m.poke_w(m.addr("FAT_FATSTART"), FATSTART)
    m.poke(m.addr("FAT_NUMFATS"), NUMFATS)
    m.poke_w(m.addr("FAT_SECPERFAT"), SECPERFAT)
    # M30: fat_alloc_cluster now scans from FAT_ALLOCHINT (fat_mount resets it to
    # 2 at the start of every real operation); this test calls fat_alloc_cluster
    # directly without going through fat_mount, so seed it here to match.
    m.poke_w(m.addr("FAT_ALLOCHINT"), 2)
    return m, fat


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    # --- clusters 2,3,4 used -> first free is 5 -------------------------------
    m, fat = make_machine(used_clusters={2, 3, 4})
    cpu = m.call("fat_alloc_cluster")
    ok = not carry(cpu)
    check(ok, "fat_alloc_cluster (2-4 used) -> Cy=0 (allocated)")
    check((cpu.hl & 0xFFFF) == 5, f"  allocated cluster = {cpu.hl & 0xFFFF} (want 5)")
    # the claim must have written EOC: the verified reader reads it as end-of-chain
    back = m.call("fat_next_cluster", hl=5).hl & 0xFFFF
    check(back >= 0x0FF8, f"  cluster 5 now reads back {back:#05x} (>= 0x0FF8, EOC)")

    # --- whole FAT full -> disk-full ------------------------------------------
    m2, _ = make_machine(used_clusters=set(range(2, TOTAL)))
    cpu2 = m2.call("fat_alloc_cluster")
    check(carry(cpu2), "fat_alloc_cluster (all used) -> Cy=1 (disk full)")

    print()
    print("ALL PASS — fat_alloc_cluster claims the first free cluster as EOC"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
