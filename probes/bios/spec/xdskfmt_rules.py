#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/disk/DSKFMT.md's EXECUTABLE RULES (docs/spec-method.md §3a): DSKFMT ($401C in the disk ROM) from the XDFMT1
probe, run 2 (scratchpad/XDFMT1_run2.out, the CF-3300 row: the National CF-3300 against zerobas's disk build --
zerobas's disk target is the CF-3300's interface). probes/bios/spec/xdfmt1.asm documents the cases and the 38-byte
record: A, F, B, C, D, E, H, L after DSKFMT, the interrupt state, PHYDIO's A and F reading sectors 0-1 back, the boot
sector's bytes 11-29 (the BPB), sector 1's first 4 bytes (the FAT), 4 x $00."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
from xgetdpb_rules import FMT  # noqa: E402

PAGE = "docs/disk/DSKFMT.md"
OUTPUTS = {"XF": ["a", "f", "b", "c", "de", "hl", "iff", "pa", "pf", "bpb", "fat"]}
CHOICES = [0, 5, 1, 2, 3, 4]
MEDIA = {1: 0xFC, 2: 0xFD, 3: 0xF8, 4: 0xF9}       # the CF-3300's choices, measured
EMPTY_MEDIA = 0xF9                                  # disk/empty720.dsk, before any format


def bpb_of(media):
    """boot-sector bytes 11-29 of the standard format: bytes per sector, sectors per cluster, reserved sectors, FATs,
    root entries, total sectors, media, FAT sectors, sectors per track, sides, hidden sectors"""
    sides, spt, trk, spc, fats, root = FMT[media]
    total = sides * spt * trk
    return [0x00, 0x02, spc, 0x01, 0x00, 0x02, root, 0x00, total & 0xFF, total >> 8, media, fats, 0x00, spt, 0x00,
            sides, 0x00, 0x00, 0x00]


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XDFMT1_run2.out")).read()
    d = {"ref": [], "zb": []}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        b += bytes(max(0, 38 * len(CHOICES) - len(b)))
        last = EMPTY_MEDIA
        for i, ch in enumerate(CHOICES):
            r = b[38 * i: 38 * (i + 1)]
            d[who].append(NS(src="XF", id=f"XF {i}", choice=ch, before=last,
                             a=r[0], f=r[1], b=r[2], c=r[3], de=(r[4] << 8) | r[5], hl=(r[6] << 8) | r[7], iff=r[8],
                             pa=r[9], pf=r[10], bpb=list(r[11:30]), fat=list(r[30:34])))
            if ch in MEDIA:
                last = MEDIA[ch]
    return d


OK = lambda c: c.choice in MEDIA                    # noqa: E731
S1 = "1. DSKFMT ($401C): format the disk in drive A"
RULES = [
    Rule("R-DF-FORMAT", S1, "Choices 1-4 format drive A as the CF-3300 offers them: 1 $FC (1 side x 9 sectors x 40 "
         "tracks), 2 $FD (2 x 9 x 40), 3 $F8 (1 x 9 x 80), 4 $F9 (2 x 9 x 80). The boot sector's BPB (bytes 11-29) is "
         "that format's: 512 bytes per sector, its sectors per cluster, 1 reserved sector, 2 FATs, its root entries "
         "and total sectors, the media byte, its FAT sectors, 9 sectors per track, its sides, 0 hidden; the FAT starts "
         "media, $FF, $FF, $00.", OK,
         lambda c: c.bpb == bpb_of(MEDIA[c.choice]) and c.fat == [MEDIA[c.choice], 0xFF, 0xFF, 0x00]),
    Rule("R-DF-OKREGS", S1, "A format returns A 0, the carry clear, B 0, interrupts off; F $42, C $3C, DE $0049, HL "
         "$9020 (working values, the same for every choice).", OK,
         lambda c: (c.a, c.f & 1, c.b, c.iff) == (0, 0, 0, 0) and (c.f, c.c, c.de, c.hl) == (0x42, 0x3C, 0x0049, 0x9020)),
    Rule("R-DF-BAD", S1, "A choice the interface does not offer (0, 5) refuses before anything is written: A 12, the "
         "carry set, B $20, C 0, E = the choice - 1 (8 bits: $FF for 0), D 0, HL as entered ($8000), interrupts off; "
         "the disk keeps its format (BPB and FAT unchanged).", lambda c: not OK(c),
         lambda c: (c.a, c.f & 1, c.b, c.c, c.de, c.hl, c.iff) == (12, 1, 0x20, 0, (c.choice - 1) & 0xFF, 0x8000, 0)
         and c.bpb == bpb_of(c.before) and c.fat == [c.before, 0xFF, 0xFF, 0x00]),
    Rule("R-DF-BADF", S1, "The rest of F on a refusal: $3B for choice 0, $93 for choice 5.", lambda c: not OK(c),
         lambda c: c.f == {0: 0x3B, 5: 0x93}[c.choice]),
    Rule("R-DF-READBACK", S1, "The probe's PHYDIO read of sectors 0-1 after each call succeeds: A 0, F $42 (PHYDIO.md's "
         "good read).", lambda c: True, lambda c: (c.pa, c.pf) == (0, 0x42)),
]
