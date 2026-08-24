# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM GETDPB ($4016) field-assembly, no emulator.

GETDPB builds an 18-byte Drive Parameter Block from the mounted volume's BPB.
Its two I/O dependencies — fat_mount (reads + parses the boot sector) and
fat_total_clusters (counts data clusters) — touch the FDC hardware, so we MOCK
them: each is trapped and replaced by a Python callback that leaves exactly the
scratch a real 720 KB mount would, then returns Cy=0. GETDPB's own field
assembly then runs for real, and we assert the resulting DPB byte-for-byte
against the National CF-3300 black-box oracle (disk/PROVENANCE.md §DPB; the
values are cited inline in disk.asm:716-823).

This exercises: load disk.rom + call an internal routine by symbol, dependency
mocking, and an oracle assertion — the whole harness loop end to end.
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

ROM = tp("zerobas_disk_ut.rom")
SYM = tp("zerobas_disk_ut.sym")

# --- 720 KB volume geometry (standard MSX 9-sector, double-sided) -----------
# reserved=1, FATs=2, secPerFAT=3, rootEnt=112(->7 root secs), secPerClus=2.
#   FAT top      = reserved                    = 1
#   root top     = reserved + FATs*secPerFAT   = 1 + 6 = 7
#   data top     = root top + rootSecs(7)      = 14
#   data clusters= (1440 - 14) / 2             = 713  -> "amount+1" = 714 = 0x02CA
MEDIA, SECSIZE, ROOTENT = 0xF9, 512, 112
SECPERCLUS, FATSTART, FIRSTROOT, FIRSTDATA = 2, 1, 7, 14
NUMFATS, SECPERFAT = 2, 3
TOTAL_CLUSTERS_RET = 715           # fat_total_clusters returns dataClusters+2

# GETDPB is called with HL = (fields base - 1): it does `inc hl` and writes the
# media byte there, so the 18 DPB fields land at FIELDS..FIELDS+17. The byte
# passed in HL (FIELDS-1) is the untouched drive-number slot.
FIELDS = 0xC100


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    # disk.asm is split into parts it includes; -I disk resolves them.
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def mock_fat_mount(m):
    """Leave the scratch a real 720 KB fat_mount would, then succeed (Cy=0)."""
    sb = m.addr("SECTOR_BUF")
    m.poke(sb + 21, MEDIA)                 # BPB media descriptor
    m.poke_w(sb + 11, SECSIZE)             # BPB bytes-per-sector
    m.poke_w(sb + 17, ROOTENT)             # BPB root-entry count
    m.poke(m.addr("FAT_SECPERCLUS"), SECPERCLUS)
    m.poke_w(m.addr("FAT_FATSTART"), FATSTART)
    m.poke_w(m.addr("FAT_FIRSTROOT"), FIRSTROOT)
    m.poke_w(m.addr("FAT_FIRSTDATA"), FIRSTDATA)
    m.poke(m.addr("FAT_NUMFATS"), NUMFATS)
    m.poke(m.addr("FAT_SECPERFAT"), SECPERFAT)
    m.cpu.f &= ~0x01                        # Cy = 0 (mount ok)


def mock_total_clusters(m):
    m.cpu.de = TOTAL_CLUSTERS_RET          # DE = dataClusters + 2
    m.cpu.f &= ~0x01                        # Cy = 0


# expected DPB fields at FIELDS+0 .. FIELDS+17 (CF-3300 oracle). MSX2 TH Fig 3.11.
EXPECT = {
    0: 0xF9,                       # media ID
    1: 0x00, 2: 0x02,             # sector size 512 (LE)
    3: 0x0F,                       # directory mask  (512/32 - 1)
    4: 0x04,                       # directory shift (log2 16)
    5: 0x01,                       # cluster mask    (secPerClus - 1)
    6: 0x02,                       # cluster shift   (bits(mask) + 1)
    7: 0x01, 8: 0x00,             # FAT top sector  = 1 (LE)
    9: 0x02,                       # number of FATs
    10: 0x70,                      # directory entries = 112
    11: 0x0E, 12: 0x00,           # data top sector = 14 (LE)
    13: 0xCA, 14: 0x02,           # amount of clusters + 1 = 714 (LE)
    15: 0x03,                      # sectors per FAT
    16: 0x07, 17: 0x00,           # directory top sector = 7 (LE)
}


def run():
    build()
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    m.trap("fat_mount", mock_fat_mount)
    m.trap("fat_total_clusters", mock_total_clusters)

    cpu = m.call("getdpb", hl=FIELDS - 1, a=0, b=MEDIA, c=MEDIA)

    fails = 0
    if carry(cpu):
        print("FAIL  GETDPB returned Cy=1 (error)"); fails += 1
    else:
        print("PASS  GETDPB returned Cy=0 (success)")

    for off, want in EXPECT.items():
        got = m.mem[FIELDS + off]
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  DPB+{off:<2} {got:#04x} "
              f"{'==' if ok else '!='} {want:#04x}")

    # the bytes GETDPB must NOT touch: the drive-number slot (FIELDS-1) and the
    # FAT-in-memory pair (FIELDS+18/+19), all left at their pre-call value 0x00.
    for off in (-1, 18, 19):
        got = m.mem[FIELDS + off]
        ok = got == 0x00
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  DPB{off:+d} untouched ({got:#04x})")

    print()
    print("ALL PASS — GETDPB is byte-identical to the CF-3300 oracle"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
