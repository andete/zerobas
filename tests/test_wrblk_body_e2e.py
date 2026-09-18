# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM wrblk_body ($26 WRBLK) end-to-end, no emulator.

Drives the REAL canonical entry (wrblk_body, wired at $47BE per M28) against a
full synthetic disk image (boot sector / BPB, one FAT copy, one root-directory
sector holding a single file, and a data area) -- read_sector/write_sector are
the only mocked dependency (against an in-memory byte array), so fat_mount,
fat_find, the per-record write loop, the extend/shrink logic, and the dirent
update all run for real, exactly as they would inside the ROM.

Exercises the top-level dispatch contract (tier2-m28-blockrandom-spec.md
§3.3/[LANDED-A]) that the narrower helper tests (test_wrblk_extend.py,
test_wrblk_fsize.py) don't reach: RS resolution from the FCB, the HL==0
size-only/shrink dispatch, RR advance by HL_REQUESTED (not actual), and the
final dirent (size + first cluster) landing correctly on the synthetic disk.

Clean-room: our own routine (kernel.asm), our own synthetic disk image, the
published RANDOM BLOCK WRITE contract (map.grauw.nl) + the [LANDED-A] oracle
contract -- no stock disassembly. See disk/docs/tier2-m28-blockrandom-spec.md.
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

ROM = tp("zb_wrblk_e2e_ut.rom")
SYM = tp("zb_wrblk_e2e_ut.sym")

SECSIZE = 512
FATSTART = 1
FAT_SECTORS = 2
NUMFATS = 1
SECPERFAT = FAT_SECTORS
FIRSTROOT = FATSTART + NUMFATS * SECPERFAT
ROOTSECS = 1
FIRSTDATA = FIRSTROOT + ROOTSECS
SECPERCLUS = 1
TOTAL_CLUSTERS = 30
EOC = 0xFFF

FCB = 0xDA40


def n83(name):
    base, ext = (name.split(".") + [""])[:2]
    return (base.ljust(8) + ext.ljust(3)).encode("latin1")[:11]


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


class Disk:
    """A full synthetic FAT12 image: boot sector + BPB, 1 FAT, 1 root sector
    with a single file entry, and a data area -- addressed by ABSOLUTE logical
    sector, exactly like the real fat_mount/fat_find/read_sector/write_sector
    chain expects (fat_mount reads sector 0 for the BPB itself)."""

    def __init__(self, name, first_cluster, size, chain_links=()):
        self.boot = bytearray(SECSIZE)
        struct.pack_into("<H", self.boot, 11, SECSIZE)      # BPB_BYTSPERSEC
        self.boot[13] = SECPERCLUS                          # BPB_SECPERCLUS
        struct.pack_into("<H", self.boot, 14, FATSTART)      # BPB_RSVDSECCNT
        self.boot[16] = NUMFATS                              # BPB_NUMFATS
        struct.pack_into("<H", self.boot, 17, 16)            # BPB_ROOTENTCNT (16/sector)
        struct.pack_into("<H", self.boot, 22, SECPERFAT)     # BPB_FATSZ16

        self.fat = bytearray(FAT_SECTORS * SECSIZE)
        for c, nxt in chain_links:
            put_fat12(self.fat, c, nxt)

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

    def dirent(self):
        cluster = struct.unpack_from("<H", self.root, 26)[0]
        size = struct.unpack_from("<I", self.root, 28)[0]
        return cluster, size


def new_machine():
    return Machine(ROM, SYM, rom_base=DISK_BASE)


def setup_fcb(m, name, rs=128, rr=0):
    m.poke(FCB, bytes(37))
    m.poke(FCB + 1, n83(name))
    m.poke_w(FCB + 14, rs)
    m.poke(FCB + 33, struct.pack("<I", rr)[:3])
    m.poke_w(m.addr("DOS_DTAPTR"), 0xC000)   # arbitrary scratch DTA


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    # --- case (i): within-EOF write, record 2 of a 4-record (512B) file --------
    m = new_machine()
    disk = Disk("DATA.BIN", first_cluster=5, size=512, chain_links=[(5, EOC)])
    disk.install(m)
    setup_fcb(m, "DATA.BIN", rs=128, rr=2)
    pattern = bytes([0xC1] * 128)
    m.poke(0xC000, pattern)
    cpu = m.call("wrblk_body", de=FCB, hl=1)
    check(cpu.a == 0, f"within-EOF write: A={cpu.a} (want 0)")
    check((cpu.hl & 0xFFFF) == 1, f"  HL={cpu.hl & 0xFFFF} (want 1, requested preserved)")
    # cluster 5's sector 0 lives at data[(5-2)*SECSIZE : ...]; record 2 is the
    # 3rd 128-byte slot (record-in-sector 2) within it.
    base = (5 - 2) * SECSIZE + 2 * 128
    got = bytes(disk.data[base:base + 128])
    check(got == pattern, "  record 2's 128 bytes landed correctly in the data area")
    r0, r1, r2 = m.peek(FCB + 33, 3)
    check((r0, r1, r2) == (3, 0, 0), f"  RR advanced to {(r0,r1,r2)} (want (3,0,0), += HL_requested)")
    cluster, size = disk.dirent()
    check(size == 512, f"  dirent size unchanged at {size} (write stayed within EOF)")

    # --- case (ii): past-EOF extend -- write record 4 of a 4-record (512B) file,
    # growing it into a second cluster (contiguous chain, not sparse).
    m = new_machine()
    disk = Disk("DATA.BIN", first_cluster=5, size=512, chain_links=[(5, EOC)])
    disk.install(m)
    setup_fcb(m, "DATA.BIN", rs=128, rr=4)
    pattern = bytes([0xC2] * 128)
    m.poke(0xC000, pattern)
    cpu = m.call("wrblk_body", de=FCB, hl=1)
    check(cpu.a == 0, f"past-EOF extend: A={cpu.a} (want 0)")
    check(get_fat12(disk.fat, 5) != 0 and get_fat12(disk.fat, 5) < 0x0FF8,
          "  cluster 5 now links onward (contiguous extend, not left as EOC)")
    new_tail = get_fat12(disk.fat, 5)
    check(get_fat12(disk.fat, new_tail) >= 0x0FF8, "  the new tail cluster is EOC")
    # record 4 lives at byte offset 512 -- the NEW cluster's sector 0, record-in-
    # sector 0. Cluster c's sector 0 lives at data[(c-2)*SECPERCLUS*SECSIZE : ...].
    new_tail_bytes = bytes(disk.data[(new_tail - 2) * SECSIZE:(new_tail - 2) * SECSIZE + 128])
    check(new_tail_bytes == pattern, "  record 4's 128 bytes landed in the newly allocated cluster")
    cluster, size = disk.dirent()
    check(size == 640, f"  dirent size grew to {size} (want 640 = 5 records * 128)")
    r0, r1, r2 = m.peek(FCB + 33, 3)
    check((r0, r1, r2) == (5, 0, 0), f"  RR advanced to {(r0,r1,r2)} (want (5,0,0))")

    # --- case (iii): HL=0, RR at/past EOF -> size bump only, no data, no chain
    # change beyond what already exists.
    m = new_machine()
    disk = Disk("DATA.BIN", first_cluster=5, size=256, chain_links=[(5, EOC)])
    disk.install(m)
    setup_fcb(m, "DATA.BIN", rs=128, rr=4)     # RR*RS = 512 > old size 256
    cpu = m.call("wrblk_body", de=FCB, hl=0)
    check(cpu.a == 0, f"HL=0 beyond-EOF: A={cpu.a} (want 0)")
    check((cpu.hl & 0xFFFF) == 0, f"  HL={cpu.hl & 0xFFFF} (want 0, preserved)")
    cluster, size = disk.dirent()
    check(size == 512, f"  dirent size set to {size} (want 512 = RR*RS, no data written)")
    check(get_fat12(disk.fat, 5) >= 0x0FF8, "  chain untouched (still just cluster 5, EOC)")
    r0, r1, r2 = m.peek(FCB + 33, 3)
    check((r0, r1, r2) == (4, 0, 0), "  RR unchanged (+= 0)")

    # --- case (iv): HL=0, RR before EOF -> SANE shrink (§6 Q3 divergence) ------
    m = new_machine()
    disk = Disk("DATA.BIN", first_cluster=5, size=1536,
                chain_links=[(5, 6), (6, 7), (7, EOC)])   # 3 clusters, 512B each
    disk.install(m)
    setup_fcb(m, "DATA.BIN", rs=128, rr=2)     # RR*RS = 256 < old size 1536 -> shrink
    cpu = m.call("wrblk_body", de=FCB, hl=0)
    check(cpu.a == 0, f"HL=0 shrink: A={cpu.a} (want 0, SANE shrink succeeds)")
    cluster, size = disk.dirent()
    check(size == 256, f"  dirent size shrunk to {size} (want 256 = RR*RS)")
    check(get_fat12(disk.fat, 5) >= 0x0FF8, "  cluster 5 (holds byte 256) is now the EOC tail")
    check(get_fat12(disk.fat, 6) == 0, "  cluster 6 freed")
    check(get_fat12(disk.fat, 7) == 0, "  cluster 7 freed")

    # === fsize_body end-to-end (real fat_mount/fat_find against the same disk) =
    m = new_machine()
    disk = Disk("DATA.BIN", first_cluster=5, size=640, chain_links=[(5, EOC)])
    disk.install(m)
    m.poke(FCB, bytes(37))
    m.poke(FCB + 1, n83("DATA.BIN"))
    cpu = m.call("fsize_body", de=FCB)
    check(cpu.a == 0 and (cpu.hl & 0xFF) == 0, f"fsize_body found: A={cpu.a} L={cpu.hl & 0xFF}")
    r0, r1, r2 = m.peek(FCB + 33, 3)
    check((r0, r1, r2) == (5, 0, 0), f"  r0..r2={(r0,r1,r2)} (want (5,0,0), ceil(640/128)=5)")

    m2 = new_machine()
    disk2 = Disk("DATA.BIN", first_cluster=5, size=640, chain_links=[(5, EOC)])
    disk2.install(m2)
    m2.poke(FCB, bytes(37))
    m2.poke(FCB + 1, n83("NOSUCH.TXT"))
    cpu = m2.call("fsize_body", de=FCB)
    check(cpu.a == 0xFF and (cpu.hl & 0xFF) == 0xFF,
          f"fsize_body not-found: A={cpu.a} L={cpu.hl & 0xFF} (want $FF/$FF)")

    print()
    print("ALL PASS — wrblk_body + fsize_body end-to-end against a synthetic disk"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
