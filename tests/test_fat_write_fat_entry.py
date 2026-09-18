# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM fat_write_fat_entry (FAT12 write-side 12-bit pack), no emul.

fat_write_fat_entry is the exact inverse of fat_next_cluster: in HL = cluster,
DE = 12-bit value, it packs the value into the right nibbles of the FAT sector
and writes it back to EVERY FAT copy on disk (BPB_NUMFATS of them, secPerFAT
sectors apart). Like the reader it has four pack cases — even/odd cluster, each
possibly straddling a 512-byte FAT-sector boundary — plus the multi-FAT sync.

Two dependencies touch the FDC, so we MOCK them against a synthetic in-memory
FAT image: read_sector fills the destination buffer from the image; write_sector
writes it back AND records the target sector. The pack itself runs for real.

Two orthogonal assertions:
  1. ROUND-TRIP — after writing the chain 2->3->341->682->$FFF, walk it with the
     already-proven fat_next_cluster (test_fat_next_cluster) and confirm it reads
     back byte-exact. Using the verified reader as the oracle checks the pack
     without re-deriving the nibble math here.
  2. MULTI-FAT SYNC — each write must hit the same relative sector in all NUMFATS
     copies (copy k = FAT_FATSEC + k*secPerFAT), and a straddling entry must
     write BOTH its sectors in every copy.

Clean-room: our own routine (fat.asm), our own FAT image, public Microsoft FAT
spec §3.1/§3.2 — no stock-ROM disassembly.

KNOWN BUG (found by this test, 2026-07-04): the STRADDLE cases currently FAIL
against the shipped ROM. fat_write_fat_entry's straddle test at fat.asm:579-581
checks the byteidx HIGH byte == 0, but the straddle case byteidx == 511 = 0x01FF
has high byte 1 — so a FAT entry whose low byte sits at sector offset 511 (and,
inversely, offset 255) is packed into the wrong sector, disagreeing with the
already-validated reader fat_next_cluster. A 1-byte address-neutral fix (or a ->
dec a) corrects it, but is HELD pending an emulator differential confirming stock
MSX-DOS straddles at byteidx 511 (the oracle). Until then the straddle checks are
marked XFAIL so the suite stays green while documenting the defect. When the fix
lands + is oracle-confirmed, set STRADDLE_FIXED = True to make them strict.
"""

STRADDLE_FIXED = True        # fix landed 2026-07-04 (oracle-confirmed vs stock)

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

ROM = tp("zb_fatwrite_ut.rom")
SYM = tp("zb_fatwrite_ut.sym")

FATSTART = 1
SECSIZE = 512
FAT_SECTORS = 3
FAT_BYTES = FAT_SECTORS * SECSIZE
NUMFATS = 2
SECPERFAT = 3

# cluster -> value to store; hits even/odd x straddle/non-straddle, ends in EOC.
CHAIN = [(2, 3), (3, 341), (341, 682), (682, 0xFFF)]

# Expected write-sector set per store: copy k lands at FAT_FATSEC + k*secPerFAT;
# a straddling entry also writes the following sector in every copy.
#   2  : fatofs 3    -> fatsec 1, non-straddle -> [1, 4]
#   3  : fatofs 4    -> fatsec 1, non-straddle -> [1, 4]
#   341: fatofs 511  -> fatsec 1, STRADDLE     -> [1, 4] then [2, 5]
#   682: fatofs 1023 -> fatsec 2, STRADDLE     -> [2, 5] then [3, 6]
EXPECT_SECTORS = {
    2:   [1, 4],
    3:   [1, 4],
    341: [1, 4, 2, 5],
    682: [2, 5, 3, 6],
}


def next_expect(cluster):
    return {c: v for c, v in CHAIN}[cluster]


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    fat = bytearray(FAT_BYTES)
    writes = []                              # (sector) recorded per write_sector

    def read_sector(mm):
        # in: DE = absolute sector, HL = destination buffer.
        base = (mm.cpu.de - FATSTART) * SECSIZE
        chunk = bytes(fat[base:base + SECSIZE]) if 0 <= base < FAT_BYTES else b""
        mm.poke(mm.cpu.hl, chunk.ljust(SECSIZE, b"\x00"))
        mm.cpu.f &= ~0x01

    def write_sector(mm):
        # in: DE = absolute sector, HL = source buffer; persist to the FAT image.
        sec = mm.cpu.de
        writes.append(sec)
        base = (sec - FATSTART) * SECSIZE
        if 0 <= base < FAT_BYTES:
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
    m.poke_w(m.addr("FAT_FATSTART"), FATSTART)
    m.poke(m.addr("FAT_NUMFATS"), NUMFATS)
    m.poke_w(m.addr("FAT_SECPERFAT"), SECPERFAT)

    fails = 0

    def check(ok, msg, straddle=False):
        """Strict for non-straddle; XFAIL-aware for the known straddle bug."""
        nonlocal fails
        if ok:
            print(f"{'PASS' if not straddle or STRADDLE_FIXED else 'XPASS'}  {msg}")
            return
        if straddle and not STRADDLE_FIXED:
            print(f"XFAIL {msg}  (known bug, fat.asm:579; fix held pending oracle)")
            return
        fails += 1
        print(f"FAIL  {msg}")

    # --- store every entry, checking Cy=0 and the multi-FAT write-sector set ---
    for cluster, value in CHAIN:
        writes.clear()
        cpu = m.call("fat_write_fat_entry", hl=cluster, de=value)
        straddle = ((cluster + (cluster >> 1)) & 0x1FF) == 511
        check(not carry(cpu), f"write({cluster}={value:#05x}) Cy=0")
        got, want = list(writes), EXPECT_SECTORS[cluster]
        check(got == want,
              f"write({cluster}) FAT-copy sectors {got} "
              f"{'==' if got == want else '!='} {want}", straddle=straddle)

    # --- round-trip: the verified reader must read every value back ------------
    # (depends on the straddle writes, so it is XFAIL-gated too.)
    cur, walked = 2, [2]
    for _ in range(8):
        if cur >= 0x0FF8:
            break
        cur = m.call("fat_next_cluster", hl=cur).hl & 0xFFFF
        walked.append(cur)
    want = [2, 3, 341, 682, 0xFFF]
    check(walked == want,
          f"round-trip via fat_next_cluster {walked} "
          f"{'==' if walked == want else '!='} [2, 3, 341, 682, 0xfff]",
          straddle=True)

    print()
    if fails:
        print(f"{fails} CHECK(S) FAILED")
    elif not STRADDLE_FIXED:
        print("PASS (non-straddle strict; straddle XFAIL — known bug, fix held)")
    else:
        print("ALL PASS — fat_write_fat_entry packs all 4 cases + syncs every FAT copy")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
