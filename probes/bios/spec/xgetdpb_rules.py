#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/disk/GETDPB.md's EXECUTABLE RULES (docs/spec-method.md §3a): GETDPB ($4016 in the disk ROM) from the XDENT
probes (xdent_common.py documents the cases and the record)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xdent_common as X  # noqa: E402

PAGE = "docs/disk/GETDPB.md"
OUTPUTS = {"XE": ["a", "f", "b", "c", "de", "hl", "iff", "dpb"]}
# the standard formats: media -> (sides, sectors per track, tracks, sectors per cluster, FAT sectors, root entries)
FMT = {0xF8: (1, 9, 80, 2, 2, 112), 0xF9: (2, 9, 80, 2, 3, 112), 0xFA: (1, 8, 80, 2, 1, 112),
       0xFB: (2, 8, 80, 2, 2, 112), 0xFC: (1, 9, 40, 1, 2, 64), 0xFD: (2, 9, 40, 2, 2, 112),
       0xFE: (1, 8, 40, 1, 1, 64), 0xFF: (2, 8, 40, 2, 1, 112)}


def dpb_of(media):
    """the 18 bytes a DPB holds after its drive byte, from the format's numbers (MSX disk ROM layout: media, sector
    size, directory mask / shift, cluster mask / shift, first FAT sector, FAT count, root entries, first data sector,
    clusters + 1, FAT sectors, first root sector)"""
    sides, spt, trk, spc, fats, root = FMT[media]
    total = sides * spt * trk
    first_root = 1 + 2 * fats
    first_data = first_root + root * 32 // 512
    clusters = (total - first_data) // spc
    shift = {1: 1, 2: 2}[spc]
    return [media, 0x00, 0x02, 0x0F, 0x04, spc - 1, shift, 0x01, 0x00, 0x02, root, first_data & 0xFF,
            first_data >> 8, (clusters + 1) & 0xFF, (clusters + 1) >> 8, fats, first_root & 0xFF, first_root >> 8]


def cases():
    return X.cases("GETDPB")


# D-DISKFORCBIOS (b) (2026-11-22): row N, the NMS 8250's built-in drive (XDENTn_run3.out), takes FEWER media bytes:
# $F8, $F9 and $FA as row D does (the same 18 bytes), and REFUSES $FC, $FD, $FE and $FF (XE1 N3, XE2 N5 .. N7).
def taken(c):
    return c.row == "D" or c.bin <= 0xFB


A_PER = {"D": 2, "N": 1}                    # A = A_PER x (B - $F8): the format's index, scaled per interface
HL_BASE = {"D": 0x7405, "N": 0x74D6}        # HL = base + 18 x (B - $F7): that interface's table, 18 bytes a format


S1 = "1. GETDPB ($4016): the drive parameter block a media byte names"
RULES = [
    Rule("R-GD-DPB", S1, "GETDPB writes the 18 bytes after the DPB's drive byte (HL + 1 .. HL + 18) from the MEDIA "
         "BYTE in B alone -- the disk is not read: the media byte, sector size 512, directory mask / shift $0F / 4, "
         "the cluster mask / shift, first FAT sector 1, 2 FATs, the root entries, the first data sector, the clusters "
         "+ 1, the FAT sectors and the first root sector of that standard format. Measured (cluster mask / shift, root "
         "entries, first data, clusters + 1, FAT sectors, first root): $F8 and $FD 1/2, 112, 12, 355, 2, 5; $F9 1/2, "
         "112, 14, 714, 3, 7; $FA and $FF 1/2, 112, 10, 316, 1, 3; $FC 0/1, 64, 9, 352, 2, 5; $FE 0/1, 64, 7, 314, 1, "
         "3. HL + 0 (the drive byte) and HL + 19 on are not written. C plays no part "
         "(XE1 5: C $00, and XE3 1: C $F8 -- a valid media byte -- both give B's $F9 block). It does not touch the "
         "drive: with drive A EMPTY (XE5 0) the block and the registers are the same. The NMS 8250 (row N) writes "
         "the same 18 bytes for $F8, $F9 and $FA, and refuses the rest (R-GD-REFUSE).", taken,
         lambda c: c.dpb[1:19] == dpb_of(c.bin) and c.dpb[0] == 0xE5 and c.dpb[19:21] == [0xE5, 0xE5]),
    Rule("R-GD-REGS", S1, "It returns the carry clear, BC 0, DE = the entry HL + 19 (the end of the 18-byte copy), "
         "interrupts off, and A = the format's index: 2 x (B - $F8) on the VG-8020's NMS 1200 ($F8 0 .. $FF 14), "
         "B - $F8 on the NMS 8250; the rest of F and HL are working values that follow the media byte alone on each "
         "interface (HL = the end of an 18-byte block per format in that interface's table: $7405 + 18 x (B - $F7) "
         "on the NMS 1200, $74D6 + 18 x (B - $F7) on the NMS 8250).", taken,
         lambda c: (c.f & 1, c.b, c.c, c.de, c.iff, c.a) == (0, 0, 0, X.HL_IN + 19, 0,
                                                             A_PER[c.row] * (c.bin - 0xF8))
         and c.hl == HL_BASE[c.row] + 18 * (c.bin - 0xF7)
         and all(o.f == c.f for o in cases()["ref"] if o.bin == c.bin and o.row == c.row)),
    Rule("R-GD-REFUSE", S1, "The NMS 8250 refuses the media bytes its drive has no format for ($FC, $FD, $FE, $FF): "
         "the carry set, NOTHING written at HL (the 21 bytes keep their $E5), A = B - $F8, B and C both = the media "
         "byte, DE = the entry HL + 1, HL 0, interrupts off. (The NMS 1200 takes every one of $F8 .. $FF: which "
         "media bytes GETDPB takes is the interface's.)", lambda c: not taken(c),
         lambda c: (c.f & 1, c.a, c.b, c.c, c.de, c.hl, c.iff) == (1, c.bin - 0xF8, c.bin, c.bin, X.HL_IN + 1, 0, 0)
         and c.dpb == [0xE5] * 21),
]
