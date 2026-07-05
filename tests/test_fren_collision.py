# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM fren_body ($17 FREN rename) collision pre-check, no
emulator (mirrors test_fat_dir_create.py's synthetic-root-dir technique).

M35 (tier2-m35-m36-tierc-fixes-spec.md): fren_body must refuse a rename onto
an EXISTING new name (Cy=1, A=$FF, both dirents left intact) instead of
silently overwriting the collided dirent's name in place. When the new name
is NOT present, the rename proceeds exactly as before (byte-unchanged old
path).

Drives the REAL canonical body (fren_body) against a full synthetic FAT12
image (boot sector / BPB, one root-directory sector) -- read_sector/
write_sector are the only mocked dependency (against an in-memory byte
array), so fat_mount + both fat_find calls + the rename LDIR + write_sector
all run for real.

Clean-room: our own routine (fat.asm), our own synthetic disk image, the
published MSX-DOS FREN contract + Microsoft FAT dir-entry layout -- no stock
disassembly.
"""

import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

ROM = "/tmp/zb_fren_collision_ut.rom"
SYM = "/tmp/zb_fren_collision_ut.sym"

SECSIZE = 512
FATSTART = 1
FAT_SECTORS = 2
NUMFATS = 1
SECPERFAT = FAT_SECTORS
FIRSTROOT = FATSTART + NUMFATS * SECPERFAT
ROOTSECS = 1
FIRSTDATA = FIRSTROOT + ROOTSECS

FCB = 0xDA40


def n83(name):
    base, ext = (name.split(".") + [""])[:2]
    return (base.ljust(8) + ext.ljust(3)).encode("latin1")[:11]


def dir_entry(name, cluster=5, size=100):
    e = bytearray(32)
    e[0:11] = n83(name)
    e[11] = 0x00
    struct.pack_into("<H", e, 26, cluster)
    struct.pack_into("<I", e, 28, size)
    return bytes(e)


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


class Disk:
    """Boot sector + BPB, 1 FAT (untouched by rename), 1 root sector holding
    the given dir entries -- addressed by ABSOLUTE logical sector, same
    layout/technique as test_wrblk_body_e2e.py's Disk helper."""

    def __init__(self, entries):
        self.boot = bytearray(SECSIZE)
        struct.pack_into("<H", self.boot, 11, SECSIZE)       # BPB_BYTSPERSEC
        self.boot[13] = 1                                     # BPB_SECPERCLUS
        struct.pack_into("<H", self.boot, 14, FATSTART)       # BPB_RSVDSECCNT
        self.boot[16] = NUMFATS                                # BPB_NUMFATS
        struct.pack_into("<H", self.boot, 17, 16)              # BPB_ROOTENTCNT
        struct.pack_into("<H", self.boot, 22, SECPERFAT)       # BPB_FATSZ16

        self.fat = bytearray(FAT_SECTORS * SECSIZE)

        self.root = bytearray(ROOTSECS * SECSIZE)
        off = 0
        for e in entries:
            self.root[off:off + 32] = e
            off += 32

    def region(self, sec):
        if sec == 0:
            return self.boot, 0
        if FATSTART <= sec < FATSTART + FAT_SECTORS:
            return self.fat, (sec - FATSTART) * SECSIZE
        if FIRSTROOT <= sec < FIRSTROOT + ROOTSECS:
            return self.root, (sec - FIRSTROOT) * SECSIZE
        return None, 0

    def install(self, m):
        def read_sector(mm):
            buf, off = self.region(mm.cpu.de)
            chunk = bytes(buf[off:off + SECSIZE]) if buf is not None else b"\x00" * SECSIZE
            mm.poke(mm.cpu.hl, chunk)
            mm.cpu.f &= ~0x01

        def write_sector(mm):
            buf, off = self.region(mm.cpu.de)
            if buf is not None:
                buf[off:off + SECSIZE] = bytes(mm.peek(mm.cpu.hl, SECSIZE))
            mm.cpu.f &= ~0x01

        m.trap("read_sector", read_sector)
        m.trap("write_sector", write_sector)

    def entry(self, index):
        off = index * 32
        return bytes(self.root[off:off + 11])


def setup_fcb(m, old_name, new_name):
    m.poke(FCB, bytes(37))
    m.poke(FCB + 1, n83(old_name))
    m.poke(FCB + 17, n83(new_name))


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    # --- case 1: new name ALREADY EXISTS -> Cy=1/A=$FF, both dirents intact ---
    m = Machine(ROM, SYM)
    disk = Disk([dir_entry("RENSRC.TMP", cluster=5, size=100),
                 dir_entry("RENDST.TMP", cluster=9, size=200)])
    disk.install(m)
    setup_fcb(m, "RENSRC.TMP", "RENDST.TMP")
    cpu = m.call("fren_body", de=FCB)
    check(carry(cpu), "fren collision: Cy=1 (rename refused)")
    check(cpu.a == 0xFF, f"  A={cpu.a:#04x} (want 0xFF)")
    check(disk.entry(0) == n83("RENSRC.TMP"), "  slot 0 (RENSRC.TMP) untouched")
    check(disk.entry(1) == n83("RENDST.TMP"), "  slot 1 (RENDST.TMP) untouched")

    # --- case 2: new name ABSENT -> rename proceeds normally -------------------
    m2 = Machine(ROM, SYM)
    disk2 = Disk([dir_entry("RENSRC.TMP", cluster=5, size=100)])
    disk2.install(m2)
    setup_fcb(m2, "RENSRC.TMP", "RENDST.TMP")
    cpu2 = m2.call("fren_body", de=FCB)
    check(not carry(cpu2), "fren no-collision: Cy=0 (rename succeeds)")
    check(cpu2.a == 0, f"  A={cpu2.a:#04x} (want 0x00)")
    check(disk2.entry(0) == n83("RENDST.TMP"), "  slot 0 renamed to RENDST.TMP")

    print()
    print("ALL PASS — fren_body collision pre-check"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
