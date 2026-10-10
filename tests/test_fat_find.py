# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM directory search — name_cmp/toupper + fat_find, no emulator.

Two levels, both clean-room (our own routines fat.asm/runtime.asm, our own
synthetic directory, public FAT/MSX-DOS dir-entry layout — no stock disassembly):

  * name_cmp (+toupper): compare two 11-byte 8.3 name fields case-insensitively;
    Z set iff equal. Pure in-RAM logic — tested directly, no I/O.
  * fat_find: scan the root directory for a name. Reads each root sector via
    read_sector (MOCKED with a synthetic 1-sector root dir), 16 entries/sector,
    skipping $00 (end-of-dir), $E5 (deleted) and volume-label/subdir entries
    (attr & $18). On a hit it sets FAT_FIRSTCLUS (+26) and FAT_FILESIZE (+28).

The synthetic root sector (entry 0..: COMMAND.COM, a deleted slot, a volume
label, README.TXT, then the $00 end-marker) exercises every skip path plus the
found and not-found (hit end-marker) outcomes, and case-insensitive matching.
"""

import os
from _tmp import tp
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry, zero  # noqa: E402

# The image under test is loaded at its ORG. Named here rather than
# defaulted: msxtest.Machine's old default was $4000, the retired lean
# cart's org, so a BASIC test that omitted it silently tested the lean
# build (docs/spec-lean-retire-s3-gates.md §5, F-U).
DISK_BASE = 0x4000

ROM = tp("zb_fatfind_ut.rom")
SYM = tp("zb_fatfind_ut.sym")

FIRSTROOT = 7        # first root-dir sector (720 KB BPB)
ROOTSECS = 1         # one sector = 16 entries, enough for this fixture
NAME_A = 0xC000      # scratch for name_cmp operands
NAME_B = 0xC010
SEARCH = 0xC020      # scratch for the fat_find search name


def n83(name):
    """11-byte 8.3 field from 'BASE.EXT' or an already-padded 11-char string."""
    if "." in name:
        base, ext = name.split(".")
    else:
        base, ext = name, ""
    return (base.ljust(8) + ext.ljust(3)).encode("latin1")[:11]


def dir_entry(name, attr, cluster, size, first_byte=None):
    e = bytearray(32)
    e[0:11] = n83(name)
    if first_byte is not None:
        e[0] = first_byte          # $E5 deleted / $00 end-marker
    e[11] = attr
    struct.pack_into("<H", e, 26, cluster)
    struct.pack_into("<I", e, 28, size)
    return bytes(e)


def build_root_sector():
    ents = [
        dir_entry("COMMAND.COM", 0x20, 2, 16000),
        dir_entry("OLD.BAK", 0x20, 9, 500, first_byte=0xE5),   # deleted -> skip
        dir_entry("MYVOL", 0x08, 0, 0),                        # volume label -> skip
        dir_entry("README.TXT", 0x20, 5, 1234),                # <- target
    ]
    sec = b"".join(ents)
    sec += b"\x00" * (512 - len(sec))          # entry 4 first byte $00 = end-of-dir
    return sec


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    # --- name_cmp / toupper (pure) --------------------------------------------
    cases = [
        ("README  TXT", "README  TXT", True,  "exact match"),
        ("readme  txt", "README  TXT", True,  "case-insensitive match"),
        ("READ12  TXT", "READ12  TXT", True,  "digits/spaces unchanged"),
        ("README  TXT", "READMEXTXT ", False, "mismatch"),
    ]
    for a, b, want_eq, label in cases:
        m.poke(NAME_A, n83(a))
        m.poke(NAME_B, n83(b))
        cpu = m.call("name_cmp", hl=NAME_A, de=NAME_B)
        check(zero(cpu) == want_eq, f"name_cmp {label}: Z={zero(cpu)} (want {want_eq})")

    # --- fat_find (dir scan, mocked I/O) --------------------------------------
    sector = build_root_sector()

    def mock_read_sector(mm):
        mm.poke(mm.cpu.hl, sector)             # HL = SECTOR_BUF destination
        mm.cpu.f &= ~0x01

    m.trap("read_sector", mock_read_sector)

    def find(name):
        m.poke(m.addr("FAT_FIRSTROOT"), struct.pack("<H", FIRSTROOT))
        # D-WCACHE W1: the root-sector count is FAT_FIRSTDATA - FAT_FIRSTROOT now
        # (fat_rootsecs); FAT_ROOTSECS's cell holds the cluster count.
        m.poke(m.addr("FAT_FIRSTDATA"), struct.pack("<H", FIRSTROOT + ROOTSECS))
        m.poke(SEARCH, n83(name))
        return m.call("fat_find", hl=SEARCH)

    # found: README.TXT -> Cy=0, first cluster 5, size 1234
    cpu = find("README.TXT")
    found = not carry(cpu)
    check(found, "fat_find README.TXT -> Cy=0 (found)")
    if found:
        fc = m.mem[m.addr("FAT_FIRSTCLUS")] | (m.mem[m.addr("FAT_FIRSTCLUS") + 1] << 8)
        sz = struct.unpack("<I", bytes(m.peek(m.addr("FAT_FILESIZE"), 4)))[0]
        check(fc == 5, f"  FAT_FIRSTCLUS = {fc} (want 5)")
        check(sz == 1234, f"  FAT_FILESIZE = {sz} (want 1234)")

    # case-insensitive lookup of the same file
    check(not carry(find("readme.txt")), "fat_find readme.txt (lowercase) -> found")

    # not found: skips deleted/volume, hits the $00 end-marker -> Cy=1
    check(carry(find("NOSUCH.TXT")), "fat_find NOSUCH.TXT -> Cy=1 (not found)")
    # the deleted and volume-label entries must NOT be matchable
    check(carry(find("OLD.BAK")), "fat_find OLD.BAK (deleted) -> Cy=1 (skipped)")
    check(carry(find("MYVOL")), "fat_find MYVOL (volume label) -> Cy=1 (skipped)")

    print()
    print("ALL PASS — name_cmp + fat_find directory search"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
