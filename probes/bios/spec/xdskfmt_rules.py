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
OUTPUTS["XF2"] = OUTPUTS["XF3"] = OUTPUTS["XF"]
# per run: the cases in order -- (choice, BC, HL)
RUNS = {"XDFMT1_run2.out": ("XF", [(c, 0x2000, 0x8000) for c in (0, 5, 1, 2, 3, 4)]),
        "XDFMT2_run1.out": ("XF2", [(1, 0x2000, 0x8000), (0, 0x2000, 0x8000), (6, 0x2000, 0x8000), (7, 0x2000, 0x8000),
                                    (8, 0x2000, 0x8000), (0x80, 0x2000, 0x8000), (0xFF, 0x2000, 0x8000),
                                    (5, 0x1234, 0x8800), (4, 0x3000, 0x8400)]),
        "XDFMT3_run1.out": ("XF3", [(0x81, 0x2000, 0x8000), (1, 0x2000, 0x8400), (1, 0x2000, 0x8010)])}
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
    d = {"ref": [], "zb": []}
    for run, (src, cs) in RUNS.items():
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 38 * len(cs) - len(b)))
            last = EMPTY_MEDIA                      # each run starts from a fresh copy of the empty $F9 disk
            for i, (ch, bc, hl) in enumerate(cs):
                r = b[38 * i: 38 * (i + 1)]
                d[who].append(NS(src=src, id=f"{src} {i}", choice=ch, bcin=bc, hlin=hl, before=last,
                                 a=r[0], f=r[1], b=r[2], c=r[3], de=(r[4] << 8) | r[5], hl=(r[6] << 8) | r[7],
                                 iff=r[8], pa=r[9], pf=r[10], bpb=list(r[11:30]), fat=list(r[30:34])))
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
    Rule("R-DF-OKREGS", S1, "A format returns A 0, the carry clear, B 0, interrupts off, and HL = the entry HL + $1020 "
         "($9020, $9030, $9420 for $8000, $8010, $8400 -- not the work area's size: XF3 1 has BC $2000); F $42, C $3C, "
         "D 0 and E a working value that follows the entry H ($49 for $80xx, $41 for $84xx, whatever BC).", OK,
         lambda c: (c.a, c.f & 1, c.b, c.iff, c.hl) == (0, 0, 0, 0, c.hlin + 0x1020)
         and (c.f, c.c, c.de) == (0x42, 0x3C, {0x80: 0x49, 0x84: 0x41}[c.hlin >> 8])),
    Rule("R-DF-BAD", S1, "Every choice the interface does not offer (0, 5, 6, 7, 8, $80, $81, $FF measured: no high bit "
         "is masked away) is refused and "
         "nothing is written: A 12, the carry set, BC and HL as entered ($2000 / $8000, $1234 / $8800), D 0, E = the "
         "choice - 1 (8 bits: $FF for 0), interrupts off; the disk keeps the format it had -- the empty disk's $F9, "
         "or the $FC an earlier format wrote (XF2 1-7).", lambda c: not OK(c),
         lambda c: (c.a, c.f & 1, c.b, c.c, c.de, c.hl, c.iff)
         == (12, 1, c.bcin >> 8, c.bcin & 0xFF, (c.choice - 1) & 0xFF, c.hlin, 0)
         and c.bpb == bpb_of(c.before) and c.fat == [c.before, 0xFF, 0xFF, 0x00]),
    Rule("R-DF-BADF", S1, "The rest of F on a refusal (working flags of the choice's range test): $3B for choices 0 and "
         "$FF, $93 for 5-8, $BB for $80, $87 for $81.", lambda c: not OK(c),
         lambda c: c.f == (0x3B if c.choice in (0, 0xFF) else 0xBB if c.choice == 0x80 else 0x87 if c.choice == 0x81
                           else 0x93)),
    Rule("R-DF-READBACK", S1, "The probe's PHYDIO read of sectors 0-1 after each call succeeds: A 0, F $42 (PHYDIO.md's "
         "good read).", lambda c: True, lambda c: (c.pa, c.pf) == (0, 0x42)),
]
