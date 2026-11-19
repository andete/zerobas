#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The shared loader for the tape region's EXECUTABLE RULES (STMOTR, TAPIOF, TAPOOF, TAPOON, TAPOUT, TAPION, TAPIN;
docs/spec-method.md §3a): scratchpad/XTAP1_run1.out (rows N and D; probes/bios/spec/xtap1.asm documents the steps:
10-byte records -- A F B C D E H L, the interrupt state, port C -- and, for the TAPOUT / TAPIN loops, A and F)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

RUN = "XTAP1_run1.out"
FULL = ["a", "f", "bc", "de", "hl", "iff", "aa"]
OUTPUTS = {"XT": FULL, "XTW": ["f", "iff", "aa"], "XTL": ["a", "f"], "XTO": ["f"]}
# (call, A, F, interrupts on entry, port C preset or None, record: offset, length 10 / 2)
STEPS = ([("STMOTR", a, 0x00, 0, pc) for a, pc in ((0, 0x50), (1, 0x50), (0, 0x40), (1, 0x40), (0xFF, 0x50), (0xFF, 0x40),
                                                  (0x80, 0x50), (2, 0x40))]
         + [("STMOTR", 1, 0xFF, 1, 0x50), ("TAPIOF", 0xA7, 0x00, 0, 0x40), ("TAPIOF", 0xA7, 0xFF, 1, 0x40),
            ("TAPOOF", 0xA7, 0x00, 0, 0x40), ("TAPOOF", 0xA7, 0xFF, 1, 0x40), ("TAPOON", 0xFF, 0x00, 1, 0x50)]
         + [("TAPOUT", b, None, 0, None) for b in (0x00, 0x55, 0xAA, 0xFF)]
         + [("TAPOOF", 0xA7, 0x00, 0, None), ("TAPION", 0xA7, 0x00, 1, 0x50)]
         + [("TAPIN", k, None, 0, None) for k in range(4)]
         + [("TAPIOF", 0xA7, 0x00, 0, None)])
WRITTEN = (0x00, 0x55, 0xAA, 0xFF)


def offsets():
    off, out = 0, []
    for st in STEPS:
        n = 2 if st[0] in ("TAPOUT", "TAPIN") else 10
        out.append((off, n))
        off += n
    return out


def load(call, group="XT"):
    out = {"ref": [], "zb": []}
    text = open(os.path.join(ROOT, "scratchpad", RUN)).read()
    secs = re.findall(r"===== \S+ (nodisk|disk): .*?CAP ref : (\w+)\n  CAP ours: (\w+)", text, re.S)
    if [s[0] for s in secs] != ["nodisk", "disk"]:
        sys.exit(f"FAIL: {RUN} does not hold the nodisk and disk sections")
    offs = offsets()
    for rowname, hr, hz in secs:
        row = "N" if rowname == "nodisk" else "D"
        for who, h in (("ref", hr), ("zb", hz)):
            b = bytes.fromhex(h)
            if len(b) < offs[-1][0] + offs[-1][1]:
                sys.exit(f"FAIL: the {RUN} {rowname} {who} block is short")
            for i, ((name, ca, cf, ei, pc), (o, n)) in enumerate(zip(STEPS, offs)):
                if name != call:
                    continue
                r = b[o:o + n]
                d = dict(src=group, id=f"XT {row}{i:02}", i=i, row=row, ca=ca, cf=cf, ei=ei,
                         cpc=pc, a=r[0], f=r[1])
                if n == 10:
                    d.update(bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7], iff=r[8], aa=r[9])
                out[who].append(NS(**d))
    return out


def regs_kept(c):
    return (c.a, c.f, c.bc, c.de, c.hl) == (c.ca, c.cf, 0x1357, 0x9BDF, 0x2468)


def motor(c):
    """the motor relay, port C bit 4: 0 = running"""
    return 0 if c.aa & 0x10 == 0 else 1
