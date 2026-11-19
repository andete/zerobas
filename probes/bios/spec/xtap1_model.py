#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The shared loader for the tape region's EXECUTABLE RULES (STMOTR, TAPIOF, TAPOOF, TAPOON, TAPOUT, TAPION, TAPIN;
docs/spec-method.md §3a): scratchpad/XTAP1_run2.out and XTAP2_run1.out (rows N and D; probes/bios/spec/xtap1.asm / xtap2.asm document the steps:
10-byte records -- A F B C D E H L, the interrupt state, port C -- and, for the TAPOUT / TAPIN loops, A and F, then port C once)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

FULL = ["a", "f", "bc", "de", "hl", "iff", "aa"]
OUTPUTS = {"XT": FULL, "XTW": ["f", "iff", "aa"], "XTL": ["a", "f"], "XTO": ["f"]}
D = 0x9BDF
WRITTEN = (0x00, 0x55, 0xAA, 0xFF, 0x01, 0x80, 0x7F, 0xFE)
# (call, A, F, interrupts on entry, port C preset or None, DE): None = the port C the loop before it recorded
STEPS1 = ([("STMOTR", a, 0x00, 0, pc, D) for a, pc in ((0, 0x50), (1, 0x50), (0, 0x40), (1, 0x40), (0xFF, 0x50),
                                                      (0xFF, 0x40), (0x80, 0x50), (2, 0x40))]
          + [("STMOTR", 1, 0xFF, 1, 0x50, D), ("TAPIOF", 0xA7, 0x00, 0, 0x40, D), ("TAPIOF", 0xA7, 0xFF, 1, 0x40, D),
             ("TAPOOF", 0xA7, 0x00, 0, 0x40, D), ("TAPOOF", 0xA7, 0xFF, 1, 0x40, D),
             ("TAPOON", 0xFF, 0x00, 1, 0x50, 0x1234)]
          + [("TAPOUT", b, None, 0, None, None) for b in WRITTEN] + [("PORTC",)]
          + [("TAPOOF", 0xA7, 0x00, 0, None, D), ("TAPION", 0xA7, 0x00, 1, 0x50, 0x4321)]
          + [("TAPIN", k, None, 0, None, None) for k in range(len(WRITTEN))] + [("PORTC",)]
          + [("TAPIOF", 0xA7, 0x00, 0, None, D)])
STEPS2 = ([("STMOTR", a, f, ei, pc, D) for a, f, ei, pc in (
    (0x00, 0, 0, 0xA0), (0x01, 0, 0, 0xA0), (0xFF, 0, 0, 0xA0), (0xFF, 0, 0, 0xE0), (0x00, 0, 0, 0xF0), (0x7F, 0, 0, 0x50),
    (0xFE, 0, 0, 0x50), (0x81, 0, 0, 0x50), (0x00, 0xFF, 1, 0x40), (0xFF, 0xFF, 1, 0x40), (0xFF, 0xFF, 1, 0x50))]
          + [(nm, a, 0x00, 0, pc, D) for nm in ("TAPIOF", "TAPOOF") for a, pc in ((0x3C, 0xE0), (0x3C, 0xA0), (0xA7, 0x50),
                                                                                 (0xA7, 0x70))])
SOURCES = (("XT", "XTAP1_run2.out", STEPS1), ("XU", "XTAP2_run1.out", STEPS2))


def load(call, group="XT"):
    out = {"ref": [], "zb": []}
    for tag, run, steps in SOURCES:
        text = open(os.path.join(ROOT, "scratchpad", run)).read()
        secs = re.findall(r"===== \S+ (nodisk|disk): .*?CAP ref : (\w+)\n  CAP ours: (\w+)", text, re.S)
        if [s[0] for s in secs] != ["nodisk", "disk"]:
            sys.exit(f"FAIL: {run} does not hold the nodisk and disk sections")
        for rowname, hr, hz in secs:
            row = "N" if rowname == "nodisk" else "D"
            for who, h in (("ref", hr), ("zb", hz)):
                b = bytes.fromhex(h)
                off, pc_rec, n_case = 0, None, 0
                for st in steps:
                    if st[0] == "PORTC":
                        pc_rec = b[off]
                        off += 1
                        continue
                    name, ca, cf, ei, pc, de = st
                    n = 2 if name in ("TAPOUT", "TAPIN") else 10
                    if off + n > len(b):
                        sys.exit(f"FAIL: the {run} {rowname} {who} block is short")
                    r = b[off:off + n]
                    i = n_case
                    off += n
                    n_case += 1
                    if pc is None and n == 10:
                        pc = pc_rec
                    if name != call:
                        continue
                    d = dict(src=group, id=f"{tag} {row}{i:02}", i=i, row=row, ca=ca, cf=cf, ei=ei, cpc=pc, cde=de,
                             a=r[0], f=r[1])
                    if n == 10:
                        d.update(bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7], iff=r[8], aa=r[9])
                    out[who].append(NS(**d))
    return out


def regs_kept(c):
    return (c.a, c.f, c.bc, c.de, c.hl) == (c.ca, c.cf, 0x1357, c.cde, 0x2468)


def motor(c):
    """the motor relay, port C bit 4: 0 = running"""
    return 0 if c.aa & 0x10 == 0 else 1
