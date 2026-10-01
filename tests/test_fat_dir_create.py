# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM fat_dir_create (root-directory slot create), no emulator.

fat_dir_create scans the root directory for the first usable 32-byte slot — a
$00 end-marker OR a $E5 deleted entry OR an existing same-name entry — stamps the
11-byte 8.3 name into it, sets the attribute byte (+11), zeros the rest
(+12..31) and stamps the date 0821h at +24..25 (as the CF-3300; Joost
2026-10-01), records the slot's location in BDOS_DIRSEC/BDOS_DIROFF (for the later
Close-time fat_dir_update), and writes the sector back. read_sector/write_sector
are MOCKED against a synthetic root-dir image; the scan + stamp run for real.

Checks: a fresh file lands in the first $00 slot; a delete leaves a $E5 slot that
is REUSED ahead of later free slots; the stamped bytes (name, +11, zeroed tail)
and the recorded BDOS_DIRSEC/BDOS_DIROFF are correct.

Clean-room: our own routine (fat.asm/runtime.asm), our own dir image, public
MSX-DOS 32-byte dir-entry layout — no stock disassembly.
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

ROM = tp("zb_dircreate_ut.rom")
SYM = tp("zb_dircreate_ut.sym")

FIRSTROOT, ROOTSECS, SECSIZE = 7, 7, 512     # 112 entries / 16 = 7 sectors


def n83(name):
    base, ext = (name.split(".") + [""])[:2]
    return (base.ljust(8) + ext.ljust(3)).encode("latin1")[:11]


def used_entry(name):
    e = bytearray(32)
    e[0:11] = n83(name)
    e[11] = 0x20
    return bytes(e)


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def make_machine(entries):
    """entries: list of 32-byte dir entries laid into root sector 0; the rest of
    the root directory is $00 (free)."""
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    # D-DOSDATE: disk.rom stamps the DOS date (DATE_DAYS), which disk-ROM init
    # leaves at 1461 = 1984-01-01, as the CF-3300 has from boot. Seed it so.
    m.poke_w(m.addr("DATE_DAYS"), 1461)
    img = bytearray(ROOTSECS * SECSIZE)
    off = 0
    for e in entries:
        img[off:off + 32] = e
        off += 32

    def read_sector(mm):
        base = (mm.cpu.de - FIRSTROOT) * SECSIZE
        chunk = bytes(img[base:base + SECSIZE]) if 0 <= base < len(img) else b""
        mm.poke(mm.cpu.hl, chunk.ljust(SECSIZE, b"\x00"))
        mm.cpu.f &= ~0x01

    def write_sector(mm):
        base = (mm.cpu.de - FIRSTROOT) * SECSIZE
        if 0 <= base < len(img):
            img[base:base + SECSIZE] = bytes(mm.peek(mm.cpu.hl, SECSIZE))
        mm.cpu.f &= ~0x01

    m.trap("read_sector", read_sector)
    m.trap("write_sector", write_sector)
    # D-FATENG Option 2: the shared FAT body writes through
    # `fatprim_write_sector`, not disk's own `write_sector` (which
    # the BDOS half still uses). Trapping only the old name let the
    # engine's writes through untrapped, so the simulated FAT never
    # updated and the cluster read back 0x000.
    m.trap("fatprim_write_sector", write_sector)
    m.poke_w(m.addr("FAT_FIRSTROOT"), FIRSTROOT)
    m.poke_w(m.addr("FAT_ROOTSECS"), ROOTSECS)
    return m, img


NAME_PTR = 0xC040


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    def create(m, name):
        m.poke(NAME_PTR, n83(name))
        return m.call("fat_dir_create", hl=NAME_PTR)

    def assert_slot(m, img, name, exp_index):
        """Verify the stamped slot at exp_index + the BDOS_DIRSEC/DIROFF record."""
        off = exp_index * 32
        stamped = bytes(img[off:off + 11])
        check(stamped == n83(name), f"  name stamped at slot {exp_index}: "
              f"{stamped!r} == {n83(name)!r}")
        check(img[off + 11] == 0x00, f"  attr byte (+11) = {img[off + 11]:#04x} (want 0x00)")
        # Joost 2026-10-01 "Stamp as 3300": the tail is zero EXCEPT the date at
        # +24..25 = 0821h (1984-01-01, the CF-3300's stamp); time +22..23 stays 0.
        want_tail = b"\x00" * 12 + b"\x21\x08" + b"\x00" * 6
        check(bytes(img[off + 12:off + 32]) == want_tail,
              "  tail (+12..31) zeroed but for the date 0821h at +24..25")
        ds = m.mem[m.addr("BDOS_DIRSEC")] | (m.mem[m.addr("BDOS_DIRSEC") + 1] << 8)
        do = m.mem[m.addr("BDOS_DIROFF")] | (m.mem[m.addr("BDOS_DIROFF") + 1] << 8)
        check(ds == FIRSTROOT, f"  BDOS_DIRSEC = {ds} (want {FIRSTROOT})")
        check(do == off, f"  BDOS_DIROFF = {do} (want {off})")

    # --- case 1: first free ($00) slot after two used entries -> index 2 ------
    m, img = make_machine([used_entry("COMMAND.COM"), used_entry("AUTOEXEC.BAT")])
    check(not carry(create(m, "NEWFILE.DAT")), "fat_dir_create NEWFILE.DAT -> Cy=0")
    assert_slot(m, img, "NEWFILE.DAT", exp_index=2)

    # --- case 2: a $E5 deleted slot is reused ahead of later free slots -------
    deleted = bytearray(used_entry("OLD.BAK"))
    deleted[0] = 0xE5
    m2, img2 = make_machine([used_entry("COMMAND.COM"), bytes(deleted),
                             used_entry("KEEP.ME")])
    check(not carry(create(m2, "REUSE.ME")), "fat_dir_create REUSE.ME -> Cy=0")
    assert_slot(m2, img2, "REUSE.ME", exp_index=1)      # reuses the deleted slot
    # the entries around it must be untouched
    check(bytes(img2[0:11]) == n83("COMMAND.COM"), "  slot 0 (COMMAND.COM) untouched")
    check(bytes(img2[64:75]) == n83("KEEP.ME"), "  slot 2 (KEEP.ME) untouched")

    print()
    print("ALL PASS — fat_dir_create stamps the first usable slot + records it"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
