#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/disk/DSKIO.md's EXECUTABLE RULES (docs/spec-method.md §3a): the disk ROM's DSKIO ($4010) called DIRECTLY
(CALSLT into the interface's slot), from the XDSKIO1 probe -- XDSK1's eleven PHYDIO cases (probes/bios/spec/xdsk1.asm)
with the call replaced -- on the disk row (scratchpad/XDSKIO1_run1.out, the VG-8020 + NMS 1200) and the CF-3300 row
(XDSKIO1_run2.out). The expected values are the SAME reference's answers to the same inputs through PHYDIO ($0144):
XDSK1_run2.out (the VG-8020 + NMS 1200, docs/bios/PHYDIO.md's round 1) and XDSK1_cf3300.out (the CF-3300)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/disk/DSKIO.md"
REC = 14
CASE = re.compile(r";\s+(\d\d): (.*?): A (\d), F \$([0-9A-F]{2}), B (\d+), C \$([0-9A-F]{2}), DE (\d+), "
                  r"HL \$([0-9A-F]{4}), (di|ei), fill (E5|PAT)")
OUTS = ["a", "f", "b", "c", "de", "hl", "iff", "sum", "b0", "b512"]
OUTPUTS = {"XI": OUTS, "XI2": OUTS}
# per round: (the probe, its source tag, [(row tag, DSKIO run, the section's row name, PHYDIO run, its row name)])
ROUNDS = [("xdskio1.asm", "XI", [("D", "XDSKIO1_run1.out", "disk", "XDSK1_run2.out", "disk"),
                                 ("C", "XDSKIO1_run2.out", "cf3300", "XDSK1_cf3300.out", "cf3300")]),
          ("xdskio2.asm", "XI2", [("D", "XDSKIO2_run1.out", "disk", "XDSKIO2P_run1.out", "disk"),
                                   ("C", "XDSKIO2_run2.out", "cf3300", "XDSKIO2P_run2.out", "cf3300")])]


def _section(run, row):
    t = open(os.path.join(ROOT, "scratchpad", run)).read()
    sec = t[t.index(f" {row}: "):]
    return sec[:sec.index("\n=====")] if "\n=====" in sec else sec


def _recs(sec, key, n):
    b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", sec).group(1))
    return b + bytes(max(0, REC * n - len(b)))


def _vals(r):
    return dict(a=r[0], f=r[1], b=r[2], c=r[3], de=(r[4] << 8) | r[5], hl=(r[6] << 8) | r[7], iff=r[8],
                sum=r[9] | (r[10] << 8), b0=r[11], b512=r[12])


def cases():
    d = {"ref": [], "zb": []}
    for asm, stag, rowlist in ROUNDS:
        src = open(os.path.join(HERE, asm)).read()
        rows = CASE.findall(src[:src.index("; Drive A is a fresh copy")])
        for tag, run, row, prun, prow in rowlist:
            sec = _section(run, row)
            phy = _recs(_section(prun, prow), "ref", len(rows))
            for who, key in (("ref", "ref"), ("zb", "ours")):
                b = _recs(sec, key, len(rows))
                for i, (num, title, a, f, bb, c, de, hl, ei, kind) in enumerate(rows):
                    d[who].append(NS(src=stag, id=f"{stag} {tag}{num}", row=tag, num=int(num), title=title,
                                     bin=int(bb), hlin=int(hl, 16), phy=_vals(phy[REC * i: REC * (i + 1)]),
                                     **_vals(b[REC * i: REC * (i + 1)])))
    return d


def attempted(c):
    """the sectors DSKIO began: the count less the sectors left (B after, PHYDIO's reference answer), plus the
    one that failed (the carry)"""
    return (c.bin or 256) - c.phy["b"] + (c.phy["f"] & 1)


def same_but_hl(c):
    return all(getattr(c, k) == c.phy[k] for k in OUTS if k != "hl")


S1 = "1. DSKIO called directly"
RULES = [
    Rule("R-DI-SAME", S1, "Called directly (CALSLT to $4010 in the interface's slot) with PHYDIO's inputs -- A the "
         "drive, the carry write / read, B the count, C the media byte, DE the first sector, HL the buffer -- DSKIO "
         "does what PHYDIO ($0144) does on the same machine, case for case: A (the error code), the carry, B (the "
         "sectors NOT done: 0 after a whole transfer, the count left after an error), the interrupt state after, and every byte moved (the buffer's sum, +0 and +512) -- reads, "
         "a write, past the end, B 0, the media $F8, a buffer at $8000. PHYDIO is DSKIO behind H.PHYD; nothing on "
         "its way in changes the transfer.", lambda c: True,
         lambda c: all(getattr(c, k) == c.phy[k] for k in ("a", "b", "iff", "sum", "b0", "b512"))
         and (c.f & 1) == (c.phy["f"] & 1)),
    Rule("R-DI-REGS", S1, "The rest of F, and C and DE, are PHYDIO's too on both references (working values, as "
         "PHYDIO leaves them on that machine).", lambda c: True,
         lambda c: (c.f, c.c, c.de) == (c.phy["f"], c.phy["c"], c.phy["de"])),
    Rule("R-DI-HL", S1, "HL is where the two differ: DSKIO returns HL = the address the LAST sector it attempted "
         "went (or was to go) into -- the buffer + 512 x (the sectors attempted - 1), a failed sector counting as "
         "attempted: B 3 read whole, + $400; B 3 from 1438 (two read, the third past the end), + $400; B 2 from past "
         "the end, + 0; B 0 from 1439 (one read, the second past), + $200; from $8000 and from $A401 alike. PHYDIO "
         "returns HL as entered.", lambda c: True,
         lambda c: c.hl == (c.hlin + 512 * (attempted(c) - 1)) & 0xFFFF),
]
