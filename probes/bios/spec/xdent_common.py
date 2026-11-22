#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The XDENT probes' cases, shared by docs/disk/GETDPB.md's and docs/disk/DSKCHG.md's rules (xgetdpb_rules.py,
xdskchg_rules.py): probes/bios/spec/xdent1.asm (run 1, scratchpad/XDENT1_run1.out) and xdent2.asm (run 1,
XDENT2_run1.out), row D -- the VG-8020 + NMS 1200 against zerobas's disk build (the NODISK row has no disk ROM: its
records are skipped, 0). The 30-byte record: A, F, B, C, D, E, H, L, the interrupt state after, the buffer's 21 bytes
from HL ($A400, filled with $E5 before each call)."""
import os
import re
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
HL_IN = 0xA400
# per run: the steps that record, in order -- (case id, the entry, B in, C in, what the case is)
STEPS = {
    "XDENT1_run1.out": [("XE1 0", "MTOFF", 0x00, 0x00, "MTOFF"),
                        ("XE1 1", "GETDPB", 0xF9, 0xF9, ""), ("XE1 2", "GETDPB", 0xF8, 0xF8, ""),
                        ("XE1 3", "GETDPB", 0xFF, 0xFF, ""), ("XE1 4", "GETDPB", 0xFA, 0xFA, ""),
                        ("XE1 5", "GETDPB", 0xF9, 0x00, "C $00"),
                        ("XE1 6", "DSKCHG", 0x00, 0xF9, "first, after the GETDPBs"),
                        ("XE1 7", "DSKCHG", 0x00, 0xF9, "again")],
    "XDENT2_run1.out": [("XE2 0", "DSKCHG", 0x00, 0xF9, "first"), ("XE2 1", "DSKCHG", 0x00, 0xF9, "again"),
                        ("XE2 2", "DSKCHG", 0x00, 0xF9, "after ~1 s idle"),
                        ("XE2 3", "DSKCHG", 0x00, 0xF9, "after ~3 s idle"),
                        ("XE2 4", "DSKCHG", 0x00, 0xF9, "after ~10 s idle"),
                        ("XE2 5", "GETDPB", 0xFE, 0xFE, ""), ("XE2 6", "GETDPB", 0xFC, 0xFC, ""),
                        ("XE2 7", "GETDPB", 0xFD, 0xFD, "")]}


def cases(entry):
    d = {"ref": [], "zb": []}
    for run, steps in STEPS.items():
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        sec = t[t.index(" disk: "):]
        sec = sec[:sec.index("\n=====")] if "\n=====" in sec else sec
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", sec).group(1))
            b += bytes(max(0, 30 * len(steps) - len(b)))
            for i, (cid, ent, bin_, cin, what) in enumerate(steps):
                if ent != entry:
                    continue
                r = b[30 * i: 30 * (i + 1)]
                d[who].append(NS(src="XE", id=cid, entry=ent, bin=bin_, cin=cin, what=what, run=run,
                                 a=r[0], f=r[1], b=r[2], c=r[3], de=(r[4] << 8) | r[5], hl=(r[6] << 8) | r[7],
                                 iff=r[8], dpb=list(r[9:30])))
    return d
