# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM wrblk_read_or_extend_sector + wrblk_shrink, no emulator.

These are the two genuinely NEW pieces M28's $26 WRBLK adds (tier2-m28-
blockrandom-spec.md §3.3): a fat_read_file_sector twin that ALLOCATES a
cluster and links it contiguously instead of returning EOF ([LANDED-A]'s full
past-EOF contiguous extend, §6 Q2), and the shrink-path chain-freeing +
EOF-marking (§6 Q3's "sane" divergence from stock's broken shrink).

Both run against a REAL synthetic FAT12 image (read_sector/write_sector
mocked against an in-memory byte array, same technique as
test_fat_alloc_cluster.py / test_fat_write_fat_entry.py) so the FAT pack/
unpack, cluster-chain walk, and allocation all execute for real -- only the
physical sector I/O is modelled.

Clean-room: our own routines (kernel.asm), our own synthetic FAT image,
public Microsoft FAT spec §3.2/§3.3 -- no stock disassembly.
"""

import os
from _tmp import tp
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

ROM = tp("zb_wrblk_extend_ut.rom")
SYM = tp("zb_wrblk_extend_ut.sym")

FATSTART, SECSIZE, FAT_SECTORS = 1, 512, 4
NUMFATS, SECPERFAT = 1, FAT_SECTORS
SECPERCLUS = 1                       # 1 sector/cluster keeps sector<->cluster 1:1
FIRSTDATA = FATSTART + FAT_SECTORS * SECPERFAT
TOTAL_CLUSTERS = 40                  # data clusters 2..39
EOC = 0xFFF


def put_fat12(fat, cluster, value):
    off = cluster + (cluster >> 1)
    if cluster & 1:
        fat[off] = (fat[off] & 0x0F) | ((value << 4) & 0xF0)
        fat[off + 1] = (value >> 4) & 0xFF
    else:
        fat[off] = value & 0xFF
        fat[off + 1] = (fat[off + 1] & 0xF0) | ((value >> 8) & 0x0F)


def get_fat12(fat, cluster):
    off = cluster + (cluster >> 1)
    if cluster & 1:
        return ((fat[off] & 0xF0) >> 4) | (fat[off + 1] << 4)
    return fat[off] | ((fat[off + 1] & 0x0F) << 8)


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def make_machine(chain=()):
    """Fresh machine + synthetic FAT/data image. `chain` is a list of cluster
    numbers already linked in file order (last one gets EOC); data sectors are
    filled with a byte pattern so a read can be told apart from zero/garbage."""
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    fat = bytearray(FAT_SECTORS * SECSIZE)
    data = bytearray(TOTAL_CLUSTERS * SECPERCLUS * SECSIZE)
    # pre-existing on-disk content: byte value = (sector_index & 0xFF), so a
    # freshly-read sector's content is identifiable (and distinguishable from
    # an all-zero "zero-filled" sector, which the spec says must NOT happen).
    for i in range(len(data)):
        data[i] = (i // SECSIZE) & 0xFF

    for i, c in enumerate(chain):
        nxt = chain[i + 1] if i + 1 < len(chain) else EOC
        put_fat12(fat, c, nxt)

    def read_sector(mm):
        sec = mm.cpu.de
        if FATSTART <= sec < FATSTART + FAT_SECTORS:
            base = (sec - FATSTART) * SECSIZE
            chunk = bytes(fat[base:base + SECSIZE])
        else:
            base = (sec - FIRSTDATA) * SECSIZE
            chunk = bytes(data[base:base + SECSIZE]) if 0 <= base < len(data) else b"\x00" * SECSIZE
        mm.poke(mm.cpu.hl, chunk.ljust(SECSIZE, b"\x00"))
        mm.cpu.f &= ~0x01

    def write_sector(mm):
        sec = mm.cpu.de
        if FATSTART <= sec < FATSTART + FAT_SECTORS:
            base = (sec - FATSTART) * SECSIZE
            fat[base:base + SECSIZE] = bytes(mm.peek(mm.cpu.hl, SECSIZE))
        else:
            base = (sec - FIRSTDATA) * SECSIZE
            if 0 <= base < len(data):
                data[base:base + SECSIZE] = bytes(mm.peek(mm.cpu.hl, SECSIZE))
        mm.cpu.f &= ~0x01

    m.trap("read_sector", read_sector)
    m.trap("write_sector", write_sector)
    # D-FATENG Option 2: the shared FAT body writes through
    # `fatprim_write_sector`, not disk's own `write_sector` (which
    # the BDOS half still uses). Trapping only the old name let the
    # engine's writes through untrapped, so the simulated FAT never
    # updated and the cluster read back 0x000.
    m.trap("fatprim_write_sector", write_sector)
    m.poke_w(m.addr("FAT_FATSTART"), FATSTART)
    m.poke(m.addr("FAT_NUMFATS"), NUMFATS)
    m.poke_w(m.addr("FAT_SECPERFAT"), SECPERFAT)
    m.poke(m.addr("FAT_SECPERCLUS"), SECPERCLUS)
    m.poke_w(m.addr("FAT_FIRSTDATA"), FIRSTDATA)
    m.trap("fat_total_clusters", lambda mm: (setattr(mm.cpu, "de", TOTAL_CLUSTERS),  # CF = 0: success (D-DISKFULL: alloc now reads it)
                                                          setattr(mm.cpu, "f", mm.cpu.f & ~0x01)))
    # M30: fat_alloc_cluster (reached via the extend path) now scans from
    # FAT_ALLOCHINT (fat_mount resets it to 2 at the start of every real
    # operation); this test drives wrblk_read_or_extend_sector directly without
    # going through fat_mount, so seed it here to match.
    m.poke_w(m.addr("FAT_ALLOCHINT"), 2)
    return m, fat, data


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    # === wrblk_read_or_extend_sector ===========================================

    # --- case 1: within-EOF, existing chain -- behaves like fat_read_file_sector
    m, fat, data = make_machine(chain=[5, 6, 7])
    m.poke_w(m.addr("FAT_FIRSTCLUS"), 5)
    m.poke_w(m.addr("FAT_CURCLUS"), 5)
    m.poke(m.addr("FAT_CLUSSEC"), 0)
    cpu = m.call("wrblk_read_or_extend_sector")
    check(not carry(cpu), "wroe within-existing-chain -> Cy=0")
    check(m.mem[m.addr("FAT_CURCLUS")] | (m.mem[m.addr("FAT_CURCLUS") + 1] << 8) == 5,
          "  FAT_CURCLUS unchanged (still within cluster 5's single sector)")
    check(get_fat12(fat, 5) == 6 and get_fat12(fat, 6) == 7 and get_fat12(fat, 7) == EOC,
          "  chain 5->6->7->EOC untouched")

    # --- case 2: empty file (FAT_FIRSTCLUS/FAT_CURCLUS == 0) -> allocates cluster 2
    # as the file's FIRST cluster (the empty-file special case).
    m, fat, data = make_machine(chain=[])
    m.poke_w(m.addr("FAT_FIRSTCLUS"), 0)
    m.poke_w(m.addr("FAT_CURCLUS"), 0)
    m.poke(m.addr("FAT_CLUSSEC"), 0)
    cpu = m.call("wrblk_read_or_extend_sector")
    check(not carry(cpu), "wroe empty file -> Cy=0 (allocated)")
    newclus = m.mem[m.addr("FAT_CURCLUS")] | (m.mem[m.addr("FAT_CURCLUS") + 1] << 8)
    check(newclus == 2, f"  allocated cluster {newclus} (want 2, first free)")
    firstclus = m.mem[m.addr("FAT_FIRSTCLUS")] | (m.mem[m.addr("FAT_FIRSTCLUS") + 1] << 8)
    check(firstclus == 2, f"  FAT_FIRSTCLUS updated to {firstclus} (want 2 -- the empty-file case)")
    check(get_fat12(fat, 2) >= 0x0FF8, "  new cluster 2 marked EOC")

    # --- case 3: past-EOF extend -- existing chain 5->6(EOC), advance walks off
    # the end and must ALLOCATE cluster 7, linking 6->7 (contiguous, not sparse).
    m, fat, data = make_machine(chain=[5, 6])
    m.poke_w(m.addr("FAT_FIRSTCLUS"), 5)
    m.poke_w(m.addr("FAT_CURCLUS"), 6)
    m.poke(m.addr("FAT_CLUSSEC"), SECPERCLUS)   # cluster 6 exhausted -> advance -> EOC -> extend
    cpu = m.call("wrblk_read_or_extend_sector")
    check(not carry(cpu), "wroe past-EOF extend -> Cy=0 (allocated + linked)")
    newclus = m.mem[m.addr("FAT_CURCLUS")] | (m.mem[m.addr("FAT_CURCLUS") + 1] << 8)
    check(newclus == 2, f"  extended onto cluster {newclus} (want 2, first free)")
    check(get_fat12(fat, 6) == 2, "  old tail (cluster 6) now links to the new cluster 2")
    check(get_fat12(fat, 2) >= 0x0FF8, "  new cluster 2 marked EOC")
    check(get_fat12(fat, 5) == 6, "  earlier link 5->6 undisturbed")

    # --- case 4: disk full during extend -> Cy=1, no partial link left dangling
    m, fat, data = make_machine(chain=[5])
    # mark every OTHER cluster used so fat_alloc_cluster has nothing free
    for c in range(2, TOTAL_CLUSTERS):
        if c != 5:
            put_fat12(fat, c, EOC)
    m.poke_w(m.addr("FAT_FIRSTCLUS"), 5)
    m.poke_w(m.addr("FAT_CURCLUS"), 5)
    m.poke(m.addr("FAT_CLUSSEC"), SECPERCLUS)   # cluster 5 (already EOC) -> advance -> extend
    cpu = m.call("wrblk_read_or_extend_sector")
    check(carry(cpu), "wroe disk-full during extend -> Cy=1")

    # === wrblk_shrink ===========================================================
    # Chain 5->6->7->8(EOC), 1 sector/cluster (512 B/cluster). Shrink target size
    # picked mid-chain so cluster 6 is KEPT (as the new EOC) and 7,8 are freed.

    def do_shrink(target_size, chain, filesize_hint=None):
        m, fat, data = make_machine(chain=chain)
        m.poke_w(m.addr("FAT_FIRSTCLUS"), chain[0] if chain else 0)
        struct.pack_into("<I", m.mem, m.addr("WRBLK_MULACC"), target_size)
        cpu = m.call("wrblk_shrink")
        return m, fat, cpu

    m, fat, cpu = do_shrink(700, [5, 6, 7, 8])   # 700B needs 2 sectors (512+188) -> keep 5,6
    check(not carry(cpu), "wrblk_shrink mid-chain -> Cy=0")
    check(get_fat12(fat, 6) >= 0x0FF8, "  cluster 6 (last KEPT) now EOC")
    check(get_fat12(fat, 7) == 0, "  cluster 7 (freed tail) marked free ($000)")
    check(get_fat12(fat, 8) == 0, "  cluster 8 (freed tail) marked free ($000)")
    got_size = struct.unpack("<I", m.peek(m.addr("BDOS_WRBYTES"), 4))[0]
    check(got_size == 700, f"  BDOS_WRBYTES = {got_size} (want 700, the target size)")

    # exact cluster-boundary target: 512 bytes needs exactly 1 sector -> keep only 5
    m, fat, cpu = do_shrink(512, [5, 6, 7, 8])
    check(not carry(cpu), "wrblk_shrink exact-boundary -> Cy=0")
    check(get_fat12(fat, 5) >= 0x0FF8, "  cluster 5 (last KEPT) now EOC")
    check(get_fat12(fat, 6) == 0, "  cluster 6 freed")
    check(get_fat12(fat, 7) == 0, "  cluster 7 freed")
    check(get_fat12(fat, 8) == 0, "  cluster 8 freed")

    # shrink to size 0 -> the WHOLE chain frees, file becomes clusterless
    m, fat, cpu = do_shrink(0, [5, 6, 7])
    check(not carry(cpu), "wrblk_shrink to empty -> Cy=0")
    check(get_fat12(fat, 5) == 0, "  cluster 5 freed")
    check(get_fat12(fat, 6) == 0, "  cluster 6 freed")
    check(get_fat12(fat, 7) == 0, "  cluster 7 freed")
    firstclus = m.mem[m.addr("FAT_FIRSTCLUS")] | (m.mem[m.addr("FAT_FIRSTCLUS") + 1] << 8)
    check(firstclus == 0, f"  FAT_FIRSTCLUS -> {firstclus} (want 0, clusterless)")
    got_size = struct.unpack("<I", m.peek(m.addr("BDOS_WRBYTES"), 4))[0]
    check(got_size == 0, f"  BDOS_WRBYTES = {got_size} (want 0)")

    print()
    print("ALL PASS — wrblk_read_or_extend_sector + wrblk_shrink"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
