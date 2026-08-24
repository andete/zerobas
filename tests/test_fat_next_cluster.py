# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM fat_next_cluster ($4000-page) FAT12 chain walk, no emulator.

fat_next_cluster follows one link of a FAT12 cluster chain: in HL = current
cluster, out HL = next cluster (12-bit; >= $0FF8 = end-of-chain). FAT12 packs
1.5 bytes per entry, so it has four decode cases the test must all hit:

  * EVEN cluster: next = B0 | ((B1 & $0F) << 8)
  * ODD  cluster: next = (B1 << 4) | (B0 >> 4)
  * ...each of which may STRADDLE a 512-byte FAT-sector boundary (the entry's
    low byte at offset 511, high byte in the following FAT sector).

Its one I/O dependency is read_sector (reads absolute sector DE into SECTOR_BUF),
which touches the FDC, so we MOCK it: the trap fills SECTOR_BUF from a synthetic
in-memory FAT image we pack ourselves from the public Microsoft FAT spec 12-bit
rule (disk/PROVENANCE.md §FAT12). fat_next_cluster's own offset math + nibble
assembly then runs for real. Clean-room: our own routine (fat.asm), our own FAT
image, public spec — no stock-ROM disassembly.

The single chain 2 -> 3 -> 341 -> 682 -> $FFF exercises, in order:
  2   even, non-straddle
  3   odd,  non-straddle
  341 odd,  STRADDLE (fatofs 511)
  682 even, STRADDLE (fatofs 1023) — the exact case fat.asm's comment names
  and returns the $FFF end-of-chain marker at the last hop.
"""

import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

# The image under test is loaded at its ORG. Named here rather than
# defaulted: msxtest.Machine's old default was $4000, the retired lean
# cart's org, so a BASIC test that omitted it silently tested the lean
# build (docs/spec-lean-retire-s3-gates.md §5, F-U).
DISK_BASE = 0x4000

ROM = tp("zb_fatnext_ut.rom")
SYM = tp("zb_fatnext_ut.sym")

# --- synthetic FAT12 geometry ------------------------------------------------
FATSTART = 1                 # first FAT sector (absolute), matches a 720 KB BPB
SECSIZE = 512
FAT_SECTORS = 3              # 720 KB secPerFAT; covers clusters up to ~1024
FAT_BYTES = FAT_SECTORS * SECSIZE

# The chain to lay down: cluster -> next value packed into the FAT.
CHAIN = [
    (2, 3),        # even, non-straddle
    (3, 341),      # odd,  non-straddle
    (341, 682),    # odd,  straddle (fatofs 341+170 = 511)
    (682, 0xFFF),  # even, straddle (fatofs 682+341 = 1023), -> end-of-chain
]


def put_fat12(fat, cluster, value):
    """Pack a 12-bit entry, Microsoft FAT spec §3.2 (mirrors fat_next_cluster's
    inverse: even -> low byte + high nibble; odd -> low nibble + high byte)."""
    off = cluster + (cluster >> 1)          # fatofs = cluster * 3/2
    if cluster & 1:                         # odd: B0 high nibble | B1
        fat[off] = (fat[off] & 0x0F) | ((value << 4) & 0xF0)
        fat[off + 1] = (value >> 4) & 0xFF
    else:                                   # even: B0 | B1 low nibble
        fat[off] = value & 0xFF
        fat[off + 1] = (fat[off + 1] & 0xF0) | ((value >> 8) & 0x0F)


def build_fat_image():
    fat = bytearray(FAT_BYTES)
    for cluster, value in CHAIN:
        put_fat12(fat, cluster, value)
    return fat


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    fat = build_fat_image()
    sector_buf = m.addr("SECTOR_BUF")

    def mock_read_sector(mm):
        # in: DE = absolute sector, HL = SECTOR_BUF; fill it from the FAT image.
        sec = mm.cpu.de
        rel = sec - FATSTART
        base = rel * SECSIZE
        chunk = bytes(fat[base:base + SECSIZE]) if 0 <= base < FAT_BYTES else b""
        chunk = chunk.ljust(SECSIZE, b"\x00")
        mm.poke(sector_buf, chunk)
        mm.cpu.f &= ~0x01                   # Cy = 0 (read ok)

    m.trap("read_sector", mock_read_sector)
    m.poke_w(m.addr("FAT_FATSTART"), FATSTART)

    fails = 0
    for cluster, want in CHAIN:
        cpu = m.call("fat_next_cluster", hl=cluster)
        got = cpu.hl & 0xFFFF
        ok = got == want
        fails += not ok
        kind = ("odd " if cluster & 1 else "even") + \
               (",straddle" if ((cluster + (cluster >> 1)) & 0x1FF) == 511 else "")
        print(f"{'PASS' if ok else 'FAIL'}  next({cluster}) = {got:#05x} "
              f"{'==' if ok else '!='} {want:#05x}  [{kind}]")

    # walk the whole chain end to end from the head, must terminate at >= $0FF8.
    cur, hops, walked = 2, 0, [2]
    while cur < 0x0FF8 and hops < 16:
        cur = m.call("fat_next_cluster", hl=cur).hl & 0xFFFF
        walked.append(cur)
        hops += 1
    ok = walked == [2, 3, 341, 682, 0xFFF]
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  chain walk {walked} "
          f"{'terminates at' if ok else '!= expected, last'} {cur:#05x}")

    print()
    print("ALL PASS — fat_next_cluster decodes all 4 FAT12 nibble cases"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
