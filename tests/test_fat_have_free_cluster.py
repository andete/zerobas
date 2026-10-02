# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM fat_have_free_cluster (M34 availability pre-check helper),
no emulator.

tier2-m34-wrseq-diskfull-spec.md §3.2: fat_have_free_cluster is a scan-only,
non-committing sibling of fat_alloc_cluster -- it answers "does a $000 (free)
cluster exist in FAT copy 0?" without claiming one (no fat_write_fat_entry call,
FAT_ALLOCHINT left untouched). It reuses fat_total_clusters (scan bound) and
fac_entry_from_wbuf (the shared straddle-correct 12-bit unpack), mirroring
fat_alloc_cluster's own scan structure. Dependencies mocked against a synthetic
FAT image exactly like test_fat_alloc_cluster.py: fat_total_clusters (bounds the
scan) and read_sector (serves FAT sectors); write_sector is also trapped so a
test would fail loudly if the helper ever wrote back (it must not).

Checks:
  (a) a FAT image with at least one $000 free cluster -> Cy=0 (NC).
  (b) a fully-allocated FAT (no $000 in the data-cluster range) -> Cy=1 (C).
  (c) the scan-only contract: FAT_ALLOCHINT is left exactly as seeded (never
      written), and write_sector is never called (no commit).

Clean-room: our own routine (kernel.asm), our own FAT image, public Microsoft
FAT spec §3.2 ($000 = free, $FF8-$FFF = end-of-chain) -- no stock disassembly.
"""

import os
from _tmp import tp
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

ROM = tp("zb_fathavefree_ut.rom")
SYM = tp("zb_fathavefree_ut.sym")

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

    write_calls = {"n": 0}

    def read_sector(mm):
        base = (mm.cpu.de - FATSTART) * SECSIZE
        chunk = bytes(fat[base:base + SECSIZE]) if 0 <= base < len(fat) else b""
        mm.poke(mm.cpu.hl, chunk.ljust(SECSIZE, b"\x00"))
        mm.cpu.f &= ~0x01

    def write_sector(mm):
        write_calls["n"] += 1
        base = (mm.cpu.de - FATSTART) * SECSIZE
        if 0 <= base < len(fat):
            fat[base:base + SECSIZE] = bytes(mm.peek(mm.cpu.hl, SECSIZE))
        mm.cpu.f &= ~0x01

    m.trap("read_sector", read_sector)
    m.trap("write_sector", write_sector)
    # D-FATENG Option 2: the shared FAT body writes through
    # `fatprim_write_sector`, not disk's own `write_sector` (which
    # the BDOS half still uses). Trapping only the old name let the
    # engine's writes through untrapped, so the simulated FAT never
    # updated and the cluster read back 0x000.
    m.trap("fatprim_write_sector", write_sector)
    m.trap("fat_total_clusters", lambda mm: (setattr(mm.cpu, "de", TOTAL),  # CF = 0: success (D-DISKFULL: alloc now reads it)
                                                          setattr(mm.cpu, "f", mm.cpu.f & ~0x01)))
    m.poke_w(m.addr("FAT_FATSTART"), FATSTART)
    m.poke(m.addr("FAT_NUMFATS"), NUMFATS)
    m.poke_w(m.addr("FAT_SECPERFAT"), SECPERFAT)
    return m, fat, write_calls


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    # --- (a) clusters 2,3,4 used, rest free -> a free cluster exists ----------
    m, fat, writes = make_machine(used_clusters={2, 3, 4})
    sentinel = 0xBEEF
    m.poke_w(m.addr("FAT_ALLOCHINT"), sentinel)   # must survive untouched
    cpu = m.call("fat_have_free_cluster")
    check(not carry(cpu), "fat_have_free_cluster (2-4 used, rest free) -> Cy=0 (NC, free exists)")
    hint_after = m.peek(m.addr("FAT_ALLOCHINT"), 2)
    hint_after = hint_after[0] | (hint_after[1] << 8)
    check(hint_after == sentinel,
          f"  FAT_ALLOCHINT untouched ({hint_after:#06x}, want {sentinel:#06x})")
    check(writes["n"] == 0, "  write_sector never called (scan-only, no commit)")
    # cluster 5 must still read back as FREE (the helper must not claim it)
    back = m.call("fat_next_cluster", hl=5).hl & 0xFFFF
    check(back == 0, f"  cluster 5 still reads back {back:#05x} (0 = free, not claimed)")

    # --- (b) whole FAT full (2..TOTAL-1 all used) -> no free cluster ----------
    m2, _, writes2 = make_machine(used_clusters=set(range(2, TOTAL)))
    sentinel2 = 0x1234
    m2.poke_w(m2.addr("FAT_ALLOCHINT"), sentinel2)
    cpu2 = m2.call("fat_have_free_cluster")
    check(carry(cpu2), "fat_have_free_cluster (all used) -> Cy=1 (C, none free)")
    hint2_after = m2.peek(m2.addr("FAT_ALLOCHINT"), 2)
    hint2_after = hint2_after[0] | (hint2_after[1] << 8)
    check(hint2_after == sentinel2,
          f"  FAT_ALLOCHINT untouched on disk-full path too ({hint2_after:#06x}, "
          f"want {sentinel2:#06x})")
    check(writes2["n"] == 0, "  write_sector never called on the disk-full path either")

    print()
    print("ALL PASS — fat_have_free_cluster answers free-cluster availability "
          "without claiming or disturbing state" if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
