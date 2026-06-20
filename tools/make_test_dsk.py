#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause

"""Generate a minimal 720 KB FAT12 .dsk for zerobas-disk integration testing.

The image is built from the Microsoft FAT specification + ECMA-107 geometry
(both allowed sources; see disk/PROVENANCE.md) — no disk-ROM bytes are copied.
It carries a couple of files with deterministic, easily-verified content so a
black-box read through the FDC -> FAT12 -> BDOS stack can be checked byte for
byte.

720 KB DSDD 3.5" geometry (matches disk/PROVENANCE.md §DPB):
    512 bytes/sector, 2 sectors/cluster, 1 reserved sector, 2 FATs,
    112 root entries, 1440 total sectors, media 0xF9, 3 sectors/FAT,
    9 sectors/track, 2 heads.
Sector map: 0 boot | 1-3 FAT1 | 4-6 FAT2 | 7-13 root dir | 14.. data
(cluster 2 == sector 14).

The primary test file TEST.BIN is exactly two clusters (2048 bytes = 16 records
of 128 bytes); record r is filled with the byte value r+1, so a sequential read
of record r must come back as 128 copies of (r+1). Two clusters + the 128-byte
BDOS record size exercise: per-sector refill (4 records/sector), a cluster-chain
hop (after record 8), and cluster-chain EOF (after record 16). HI.TXT is a small
second entry so the directory search has to pick the right one.

    python3 tools/make_test_dsk.py [out.dsk]      # default: disk/test720.dsk
"""
from __future__ import annotations

import os
import struct
import sys

SECTOR = 512
SEC_PER_CLUS = 2
RESERVED = 1
NUM_FATS = 2
ROOT_ENTRIES = 112
TOTAL_SECTORS = 1440
MEDIA = 0xF9
SEC_PER_FAT = 3
SEC_PER_TRACK = 9
HEADS = 2

CLUSTER_BYTES = SECTOR * SEC_PER_CLUS
FIRST_FAT = RESERVED                                   # sector 1
FIRST_ROOT = RESERVED + NUM_FATS * SEC_PER_FAT         # sector 7
ROOT_SECS = (ROOT_ENTRIES * 32 + SECTOR - 1) // SECTOR # 7
FIRST_DATA = FIRST_ROOT + ROOT_SECS                    # sector 14


class Fat12Image:
    def __init__(self):
        self.data = bytearray(TOTAL_SECTORS * SECTOR)
        # 12-bit FAT entries, indexed by cluster; 0 and 1 are reserved.
        self.fat = [0] * (TOTAL_SECTORS // SEC_PER_CLUS + 16)
        self.fat[0] = 0xF00 | MEDIA          # cluster 0 = media descriptor
        self.fat[1] = 0xFFF                  # cluster 1 = end marker
        self.next_free = 2
        self.dir_index = 0
        self._write_boot_sector()

    def _write_boot_sector(self):
        b = self.data
        b[0:3] = bytes([0xEB, 0xFE, 0x90])   # jump (harmless self-loop)
        b[3:11] = b"ZEROBAS "                 # OEM name
        struct.pack_into("<H", b, 11, SECTOR)
        b[13] = SEC_PER_CLUS
        struct.pack_into("<H", b, 14, RESERVED)
        b[16] = NUM_FATS
        struct.pack_into("<H", b, 17, ROOT_ENTRIES)
        struct.pack_into("<H", b, 19, TOTAL_SECTORS)
        b[21] = MEDIA
        struct.pack_into("<H", b, 22, SEC_PER_FAT)
        struct.pack_into("<H", b, 24, SEC_PER_TRACK)
        struct.pack_into("<H", b, 26, HEADS)
        b[510], b[511] = 0x55, 0xAA          # boot signature

    def _sector(self, n):
        return slice(n * SECTOR, (n + 1) * SECTOR)

    def add_file(self, name8, ext3, content):
        """Allocate a cluster chain, write data, add a root-dir entry."""
        assert self.dir_index < ROOT_ENTRIES, "root directory full"
        n_clusters = max(1, (len(content) + CLUSTER_BYTES - 1) // CLUSTER_BYTES)
        clusters = list(range(self.next_free, self.next_free + n_clusters))
        self.next_free += n_clusters
        # chain them, last -> end-of-chain
        for i, c in enumerate(clusters):
            self.fat[c] = clusters[i + 1] if i + 1 < len(clusters) else 0xFFF
        # write data, cluster by cluster
        padded = content + bytes(n_clusters * CLUSTER_BYTES - len(content))
        for i, c in enumerate(clusters):
            first_sec = FIRST_DATA + (c - 2) * SEC_PER_CLUS
            chunk = padded[i * CLUSTER_BYTES:(i + 1) * CLUSTER_BYTES]
            self.data[first_sec * SECTOR:first_sec * SECTOR + len(chunk)] = chunk
        # root-directory entry (Microsoft FAT spec §3.4)
        off = FIRST_ROOT * SECTOR + self.dir_index * 32
        e = self.data
        e[off:off + 8] = name8.encode("ascii").ljust(8)[:8].upper()
        e[off + 8:off + 11] = ext3.encode("ascii").ljust(3)[:3].upper()
        e[off + 11] = 0x20                    # attribute: archive
        struct.pack_into("<H", e, off + 26, clusters[0])   # first cluster
        struct.pack_into("<I", e, off + 28, len(content))  # file size
        self.dir_index += 1

    def _pack_fat(self):
        raw = bytearray(SEC_PER_FAT * SECTOR)
        for c in range(0, len(self.fat)):
            v = self.fat[c] & 0xFFF
            idx = c * 3 // 2
            if idx + 1 >= len(raw):
                break
            if c & 1:                         # odd: high nibble of idx, all idx+1
                raw[idx] = (raw[idx] & 0x0F) | ((v << 4) & 0xF0)
                raw[idx + 1] = (v >> 4) & 0xFF
            else:                             # even: all idx, low nibble of idx+1
                raw[idx] = v & 0xFF
                raw[idx + 1] = (raw[idx + 1] & 0xF0) | ((v >> 8) & 0x0F)
        return bytes(raw)

    def finish(self):
        fat = self._pack_fat()
        for copy in range(NUM_FATS):
            base = (FIRST_FAT + copy * SEC_PER_FAT) * SECTOR
            self.data[base:base + len(fat)] = fat
        return bytes(self.data)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "disk", "test720.dsk")

    img = Fat12Image()
    # TEST.BIN: 16 records of 128 bytes; record r = 128 * byte(r+1).
    test_bin = bytearray()
    for r in range(16):
        test_bin += bytes([(r + 1) & 0xFF]) * 128
    img.add_file("TEST", "BIN", bytes(test_bin))
    img.add_file("HI", "TXT", b"Hello from zerobas-disk!\r\n")

    open(out, "wb").write(img.finish())
    print(f"wrote {out} ({TOTAL_SECTORS * SECTOR} bytes)")
    print(f"  TEST.BIN : {len(test_bin)} bytes, first cluster 2 "
          f"(sectors {FIRST_DATA}.. ); record r = 128 x byte(r+1)")
    print(f"  HI.TXT   : 26 bytes")
    print(f"  geometry : firstFAT={FIRST_FAT} firstRoot={FIRST_ROOT} "
          f"rootSecs={ROOT_SECS} firstData={FIRST_DATA}")


if __name__ == "__main__":
    main()
