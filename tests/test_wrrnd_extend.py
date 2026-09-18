# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM wrrnd_body ($22 WRRND) past-EOF size extension, no
emulator (mirrors test_wrblk_body_e2e.py's synthetic-disk technique).

M36 (tier2-m35-m36-tierc-fixes-spec.md): a within-allocated-cluster past-EOF
WRRND must grow the FCB-copy's size field (ix+16..19) to (r0+1)*RECSIZE AND
persist that new size to the on-disk directory entry (the DECISIVE finding:
an FCB-only bump is a vacuous fix -- stock persists to the dirent). A
within-file WRRND (newsize <= oldsize) must leave the size field AND the
dirent completely unchanged (the existing happy-path, BDOSX3 rec18-20).

Drives the REAL canonical body (wrrnd_body) against a full synthetic FAT12
image (boot sector / BPB, one FAT, one root sector, one data cluster) --
read_sector/write_sector are the only mocked dependency, so fat_mount,
rrnd_position's seek (fat_open + fat_read_file_sector), the record overlay +
write_sector, the new size-extension math, fat_find, and the dirent patch
all run for real.

Clean-room: our own routine (kernel.asm), our own synthetic disk image, the
published MSX-DOS WRRND contract + CP/M FCB random-record layout + Microsoft
FAT dir-entry layout -- no stock disassembly.
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

ROM = tp("zb_wrrnd_extend_ut.rom")
SYM = tp("zb_wrrnd_extend_ut.sym")

SECSIZE = 512
FATSTART = 1
FAT_SECTORS = 2
NUMFATS = 1
SECPERFAT = FAT_SECTORS
FIRSTROOT = FATSTART + NUMFATS * SECPERFAT
ROOTSECS = 1
FIRSTDATA = FIRSTROOT + ROOTSECS
SECPERCLUS = 2                      # 1024 B/cluster: records 0-7 all fit in cluster 5
TOTAL_CLUSTERS = 30
EOC = 0xFFF
RECSIZE = 128

FCB = 0xDA40


def n83(name):
    base, ext = (name.split(".") + [""])[:2]
    return (base.ljust(8) + ext.ljust(3)).encode("latin1")[:11]


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


class Disk:
    """Boot sector + BPB, 1 FAT, 1 root sector holding a single file, one
    1024-byte data cluster -- same layout/technique as
    test_wrblk_body_e2e.py's Disk helper."""

    def __init__(self, name, first_cluster, size):
        self.boot = bytearray(SECSIZE)
        struct.pack_into("<H", self.boot, 11, SECSIZE)       # BPB_BYTSPERSEC
        self.boot[13] = SECPERCLUS                            # BPB_SECPERCLUS
        struct.pack_into("<H", self.boot, 14, FATSTART)       # BPB_RSVDSECCNT
        self.boot[16] = NUMFATS                                # BPB_NUMFATS
        struct.pack_into("<H", self.boot, 17, 16)              # BPB_ROOTENTCNT
        struct.pack_into("<H", self.boot, 22, SECPERFAT)       # BPB_FATSZ16

        self.fat = bytearray(FAT_SECTORS * SECSIZE)
        off = first_cluster + (first_cluster >> 1)
        # single-cluster file: mark it EOC directly (12-bit FAT12 pack)
        if first_cluster & 1:
            self.fat[off] = (self.fat[off] & 0x0F) | ((EOC << 4) & 0xF0)
            self.fat[off + 1] = (EOC >> 4) & 0xFF
        else:
            self.fat[off] = EOC & 0xFF
            self.fat[off + 1] = (self.fat[off + 1] & 0xF0) | ((EOC >> 8) & 0x0F)

        self.root = bytearray(ROOTSECS * SECSIZE)
        e = bytearray(32)
        e[0:11] = n83(name)
        e[11] = 0x00
        struct.pack_into("<H", e, 26, first_cluster)
        struct.pack_into("<I", e, 28, size)
        self.root[0:32] = e

        self.data = bytearray(TOTAL_CLUSTERS * SECPERCLUS * SECSIZE)
        for i in range(len(self.data)):
            self.data[i] = 0xAA          # pre-existing on-disk "garbage" marker

    def region(self, sec):
        if sec == 0:
            return self.boot, 0
        if FATSTART <= sec < FATSTART + FAT_SECTORS:
            return self.fat, (sec - FATSTART) * SECSIZE
        if FIRSTROOT <= sec < FIRSTROOT + ROOTSECS:
            return self.root, (sec - FIRSTROOT) * SECSIZE
        return self.data, (sec - FIRSTDATA) * SECSIZE

    def install(self, m):
        def read_sector(mm):
            buf, off = self.region(mm.cpu.de)
            mm.poke(mm.cpu.hl, bytes(buf[off:off + SECSIZE]))
            mm.cpu.f &= ~0x01

        def write_sector(mm):
            buf, off = self.region(mm.cpu.de)
            buf[off:off + SECSIZE] = bytes(mm.peek(mm.cpu.hl, SECSIZE))
            mm.cpu.f &= ~0x01

        m.trap("read_sector", read_sector)
        m.trap("write_sector", write_sector)
        # D-FATENG Option 2: the shared FAT body writes through
        # `fatprim_write_sector`, not disk's own `write_sector` (which
        # the BDOS half still uses). Trapping only the old name let the
        # engine's writes through untrapped, so the simulated FAT never
        # updated and the cluster read back 0x000.
        m.trap("fatprim_write_sector", write_sector)
        m.trap("fat_total_clusters", lambda mm: setattr(mm.cpu, "de", TOTAL_CLUSTERS))

    def dirent_size(self):
        return struct.unpack_from("<I", self.root, 28)[0]


def setup_fcb(m, name, r0, size):
    """size seeds FCB+16..19 -- the kernel FCB-copy's own size mirror, filled
    by fopen_fill_body's LDIR from FAT_FILESIZE at a real FOPEN (fat.asm
    ~1180-1188). wrrnd_extend reads ix+16..19 for oldsize, NOT FAT_FILESIZE
    directly, so this must be seeded to match mount()'s FAT_FILESIZE for the
    test to model a real post-FOPEN FCB."""
    m.poke(FCB, bytes(37))
    m.poke(FCB + 1, n83(name))
    m.poke_w(FCB + 14, RECSIZE)
    m.poke(FCB + 16, struct.pack("<I", size))
    m.poke(FCB + 33, bytes([r0, 0, 0]))


def new_machine():
    return Machine(ROM, SYM, rom_base=DISK_BASE)


def mount(m, disk, first_cluster, size):
    """fat_mount for real against the synthetic BPB (seeds FAT_SECPERCLUS/
    FAT_FIRSTDATA/etc, needed by rrnd_position's fat_open + fat_read_file_sector
    chain), then seed FAT_FIRSTCLUS/FAT_FILESIZE as a preceding kernel FOPEN
    would have left them -- wrrnd_body itself (like rdrnd_body/k47b2_body) does
    not search for the file; it only re-primes via fat_open. Same technique as
    test_rdblk_randrecord.py's make_file()."""
    cpu = m.call("fat_mount")
    assert not (cpu.f & 0x01), "fat_mount failed against the synthetic BPB"
    m.poke_w(m.addr("FAT_FIRSTCLUS"), first_cluster)
    m.poke(m.addr("FAT_FILESIZE"), struct.pack("<I", size))


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    pattern = bytes([0xC3] * RECSIZE)

    # --- case 1: past-EOF WRRND (within allocated cluster) grows the size ------
    # SHORT.DAT: 256 B (records 0,1 exist), 1 cluster (1024 B) -- WRRND r0=5
    # (byte offset 640) is past EOF but still inside the allocated cluster.
    m = new_machine()
    disk = Disk("SHORT.DAT", first_cluster=5, size=256)
    disk.install(m)
    mount(m, disk, first_cluster=5, size=256)
    setup_fcb(m, "SHORT.DAT", r0=5, size=256)
    m.poke_w(m.addr("DOS_DTAPTR"), 0xC000)
    m.poke(0xC000, pattern)
    cpu = m.call("wrrnd_body", de=FCB)
    check(not carry(cpu), f"past-EOF WRRND r0=5: Cy={carry(cpu)} (want 0)")
    check(cpu.a == 0, f"  A={cpu.a} (want 0)")
    newsize = struct.unpack_from("<I", m.peek(FCB + 16, 4))[0]
    check(newsize == 768, f"  FCB size (ix+16..19) = {newsize} (want 768 = (5+1)*128)")
    check(disk.dirent_size() == 768, f"  dirent size = {disk.dirent_size()} (want 768, PERSISTED)")
    # the record's data itself landed correctly (cluster 5 -> data[(5-2)*1024:])
    base = (5 - 2) * SECPERCLUS * SECSIZE + 640
    check(bytes(disk.data[base:base + RECSIZE]) == pattern, "  record 5's data landed at offset 640")

    # --- case 2: within-file WRRND (newsize <= oldsize) leaves size unchanged --
    # Same fixture but pre-sized to 1024 (whole cluster already "used") and
    # writing record 2 (offset 256, well within the existing size).
    m2 = new_machine()
    disk2 = Disk("SHORT.DAT", first_cluster=5, size=1024)
    disk2.install(m2)
    mount(m2, disk2, first_cluster=5, size=1024)
    setup_fcb(m2, "SHORT.DAT", r0=2, size=1024)
    m2.poke_w(m2.addr("DOS_DTAPTR"), 0xC000)
    m2.poke(0xC000, pattern)
    cpu2 = m2.call("wrrnd_body", de=FCB)
    check(not carry(cpu2), f"within-file WRRND r0=2: Cy={carry(cpu2)} (want 0)")
    check(cpu2.a == 0, f"  A={cpu2.a} (want 0)")
    unchanged = struct.unpack_from("<I", m2.peek(FCB + 16, 4))[0]
    check(unchanged == 1024, f"  FCB size (ix+16..19) = {unchanged} (want 1024, unchanged)")
    check(disk2.dirent_size() == 1024, f"  dirent size = {disk2.dirent_size()} (want 1024, unchanged)")

    # --- case 3: exact-boundary WRRND (newsize == oldsize) also skips ----------
    m3 = new_machine()
    disk3 = Disk("SHORT.DAT", first_cluster=5, size=768)
    disk3.install(m3)
    mount(m3, disk3, first_cluster=5, size=768)
    setup_fcb(m3, "SHORT.DAT", r0=5, size=768)     # (5+1)*128 == 768 == oldsize exactly
    m3.poke_w(m3.addr("DOS_DTAPTR"), 0xC000)
    m3.poke(0xC000, pattern)
    cpu3 = m3.call("wrrnd_body", de=FCB)
    check(not carry(cpu3), f"exact-boundary WRRND: Cy={carry(cpu3)} (want 0)")
    same = struct.unpack_from("<I", m3.peek(FCB + 16, 4))[0]
    check(same == 768, f"  FCB size = {same} (want 768, unchanged: newsize == oldsize)")
    check(disk3.dirent_size() == 768, f"  dirent size = {disk3.dirent_size()} (want 768, unchanged)")

    print()
    print("ALL PASS — wrrnd_body past-EOF size extension + dirent persistence"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
