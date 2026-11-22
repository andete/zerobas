#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/disk/DSKCHG.md's EXECUTABLE RULES (docs/spec-method.md §3a): DSKCHG ($4013 in the disk ROM) from the XDENT
probes (xdent_common.py documents the cases, the record and the TIMELINE). The model: the call counts TIMER
INTERRUPTS since the last DSKCHG that READ the disk. At the first call, or after 96 interrupts or more, it reads the
disk: B $FF (changed) when the disk's media byte differs from C, else B 0 (unknown). Within 48 it answers B 1
(unchanged) and reads nothing. B 1 answers, GETDPB, MTOFF and time with interrupts off do not move the clock."""
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
# D-DISKFORCBIOS (b) (2026-11-22): per INTERFACE -- row D the VG-8020's NMS 1200 (XDENTn_run1.out), row N the NMS
# 8250's built-in drive (XDENTn_run3.out). The model (the B answers, 48 / 96 interrupts, the not-ready failure) is
# the same on both, case for case; the interrupt state after the call and the working HL of a read are the
# interface's own.
IFF = {"D": 0, "N": 1}                             # interrupts after any DSKCHG: off / ON
READ_HL = {"D": 0x7429, "N": 0x74FA}               # HL after a read (a pointer into that interface's ROM)


def cases():
    return X.cases("DSKCHG")


def reads(c):
    return (c.since is None or c.since >= 96) and not c.empty


def notready(c):
    return c.empty and (c.since is None or c.since >= 96)


def recent(c):
    return c.since is not None and c.since <= 48


def expect_b(c):
    return (0xFF if DISK_MEDIA != c.cin else 0x00) if reads(c) else 0x01


S1 = "1. DSKCHG ($4013): was the disk changed"
RULES = [
    Rule("R-DC-RECENT", S1, "Within 48 timer interrupts (~1 s) of the last DSKCHG that read the disk, DSKCHG answers "
         "B 1, unchanged, and reads nothing: A 0, the carry clear, C, DE and HL as entered, the buffer "
         "at HL untouched -- C plays no part (XE4 1: C $F8, B 1). A B 1 answer does not restart the count (XE3 2 at 48 "
         "gives B 1, XE3 3 at 96 reads); nor do GETDPB (XE3 7) or MTOFF (XE4 3-4: MTOFF at 96, then a read); 3.5 s "
         "with interrupts OFF does not advance it (XE3 10: B 1 -- interrupts are counted, not time). The same on the "
         "NMS 8250 (row N), case for case. Interrupts after EVERY DSKCHG are the interface's: off on the VG-8020's "
         "NMS 1200, ON on the NMS 8250.", recent,
         lambda c: (c.b, c.a, c.f & 1, c.c, c.de, c.hl, c.iff) == (1, 0, 0, c.cin, 0, X.HL_IN, IFF[c.row])
         and c.dpb == [0xE5] * 21),
    Rule("R-DC-READ", S1, "At the first call after start-up, and after 96 interrupts or more (~2 s; 96, 176, 200 and 504 "
         "measured; 304 too -- no 8-bit wrap), DSKCHG reads the disk: A = the disk's media byte ($F9), the carry clear, C as entered, DE = the "
         "entry HL + 19, and the DPB at HL filled as GETDPB fills it for the DISK's media byte (HL + "
         "1 .. HL + 18) -- and B $FF, CHANGED, when that media byte differs from C (XE3 0, a first call, and XE4 2, a "
         "later one: C $F8), else B 0, unknown.", reads,
         lambda c: (c.b, c.a, c.f & 1, c.c, c.de, c.iff) == (expect_b(c), DISK_MEDIA, 0, c.cin, X.HL_IN + 19,
                                                             IFF[c.row])
         and c.dpb[1:19] == dpb_of(DISK_MEDIA) and c.dpb[0] == 0xE5 and c.dpb[19:] == [0xE5, 0xE5]),
    Rule("R-DC-NOTREADY", S1, "With drive A EMPTY, a call that would read fails (XE5 1, XE6 0: the first call): the "
         "carry set, A 2 (not ready), B 1, the buffer at HL untouched. A failure does not restart the "
         "count: the next call tries again and fails again (XE6 1).", notready,
         lambda c: (c.f & 1, c.a, c.b, c.iff) == (1, 2, 1, IFF[c.row]) and c.dpb == [0xE5] * 21),
    Rule("R-DC-NRREGS", S1, "The rest on that failure: F $91, C 0, DE $01F9, HL $EF97 (working values).", notready,
         lambda c: (c.f, c.c, c.de, c.hl) == (0x91, 0, 0x01F9, 0xEF97)),
    Rule("R-DC-F", S1, "F and HL when it reads: F $50 with B 0; with B $FF, $38 when C is below the disk's media byte "
         "($F8) and $B8 when above ($FA) -- the sign of the comparison, on both interfaces; HL a working value of the "
         "interface's ($7429 on the NMS 1200, $74FA on the NMS 8250 -- GETDPB returns the same HL for $F9).", reads,
         lambda c: (c.f, c.hl) == (0x50 if expect_b(c) == 0 else (0x38 if c.cin < DISK_MEDIA else 0xB8),
                                   READ_HL[c.row])),
]
