#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/disk/DSKCHG.md's EXECUTABLE RULES (docs/spec-method.md §3a): DSKCHG ($4013 in the disk ROM) from the XDENT
probes (xdent_common.py documents the cases and the record). The model: a DSKCHG within about a second of the last
disk access answers "unchanged" (B 1); the first one after the probe starts, and one after 3 s or more idle, answers
"unknown" (B 0) and reads the disk's media byte -- GETDPB does not touch the disk, so it does not count."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xdent_common as X  # noqa: E402
from xgetdpb_rules import dpb_of  # noqa: E402

PAGE = "docs/disk/DSKCHG.md"
OUTPUTS = {"XE": ["a", "f", "b", "c", "de", "hl", "iff", "dpb"]}
DISK_MEDIA = 0xF9                                   # disk/empty720.dsk


def cases():
    return X.cases("DSKCHG")


def unknown(c):
    """B 0 expected: the probe's first DSKCHG, or one after ~3 s / ~10 s idle"""
    return c.what.startswith("first") or c.what in ("after ~3 s idle", "after ~10 s idle")


S1 = "1. DSKCHG ($4013): was the disk changed"
RULES = [
    Rule("R-DC-RECENT", S1, "Within about a second of the last disk access (the call just before, or ~1 s idle) "
         "DSKCHG answers B 1, unchanged: A 0, the carry clear, C, DE and HL as entered, interrupts off, the buffer at "
         "HL untouched.", lambda c: not unknown(c),
         lambda c: (c.b, c.a, c.f & 1, c.c, c.de, c.hl, c.iff) == (1, 0, 0, c.cin, 0, X.HL_IN, 0)
         and c.dpb == [0xE5] * 21),
    Rule("R-DC-UNKNOWN", S1, "The first call after start-up, and a call after 3 s or more idle (~3 s and ~10 s "
         "measured), answer B 0, unknown, and read the disk: A = the disk's media byte ($F9), the carry clear, C as "
         "entered, DE = the entry HL + 19, interrupts off, and the DPB at HL filled as GETDPB fills it for that "
         "media byte (HL + 1 .. HL + 18). GETDPB calls before it do not count as an access (XE1 6).", unknown,
         lambda c: (c.b, c.a, c.f & 1, c.c, c.de, c.iff) == (0, DISK_MEDIA, 0, c.cin, X.HL_IN + 19, 0)
         and c.dpb[1:19] == dpb_of(DISK_MEDIA) and c.dpb[0] == 0xE5 and c.dpb[19:] == [0xE5, 0xE5]),
    Rule("R-DC-F", S1, "F and HL on the B 0 path: F $50, HL a working value ($7429 in every case).", unknown,
         lambda c: (c.f, c.hl) == (0x50, 0x7429)),
]
