# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM fat_dir_create (root-directory slot create), no emulator.

fat_dir_create scans the root directory for the first usable 32-byte slot — a
$00 end-marker OR a $E5 deleted entry OR an existing same-name entry — stamps the
11-byte 8.3 name into it, sets the attribute byte (+11) and zeros the rest
(+12..31), records the slot's location in BDOS_DIRSEC/BDOS_DIROFF (for the later
Close-time fat_dir_update), and writes the sector back. read_sector/write_sector
are MOCKED against a synthetic root-dir image; the scan + stamp run for real.

Checks: a fresh file lands in the first $00 slot; a delete leaves a $E5 slot that
is REUSED ahead of later free slots; the stamped bytes (name, +11, zeroed tail)
and the recorded BDOS_DIRSEC/BDOS_DIROFF are correct.

Clean-room: our own routine (fat.asm/runtime.asm), our own dir image, public
MSX-DOS 32-byte dir-entry layout — no stock disassembly.
"""

import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

ROM = "/tmp/zb_dircreate_ut.rom"
SYM = "/tmp/zb_dircreate_ut.sym"

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
    m = Machine(ROM, SYM)
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
        check(bytes(img[off + 12:off + 32]) == b"\x00" * 20, "  tail (+12..31) zeroed")
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
