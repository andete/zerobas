#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/disk/CHOICE.md's EXECUTABLE RULES (docs/spec-method.md §3a): the disk ROM's CHOICE ($4019) and MTOFF ($401F),
from the XCHOICE1 probe (probes/bios/spec/xchoice1.asm documents the 6 cases and the 30-byte record: A, F, B, C, D, E,
H, L, the interrupt state after, the buffer's first 21 bytes) on the disk row (scratchpad/XCHOICE1_run1.out, the
VG-8020 + NMS 1200) and the CF-3300 row (XCHOICE1_run2.out). The NODISK row has no interface and no rule reads it."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/disk/CHOICE.md"
REC = 30
FN = [("CHOICE", 0x00, 0x00), ("CHOICE", 0xF9, 0xF9), ("CHOICE", 0xFF, 0xFF),
      ("MTOFF", 0x00, 0x00), ("MTOFF", 0xFF, 0xFF), ("MTOFF", 0x12, 0x34)]
ROWS = [("D", "XCHOICE1_run1.out", "disk"), ("C", "XCHOICE1_run2.out", "cf3300"),
        ("N", "XCHOICE1_run3.out", "nms8250")]   # N: the NMS 8250 (D-DISKFORCBIOS (b))
REC2 = 41
FN2 = [("CHOICE", 0x5AD7, 0xF800, 0x1234, 0xC000), ("CHOICE", 0x0000, 0x00F9, 0x0000, 0xA400),
       ("MTOFF", 0x5AD7, 0x1234, 0x5678, 0xC000), ("DSKIO", 0x0000, 0x01F9, 0x0000, 0xA800),
       ("MTOFF", 0x0000, 0x0000, 0x0000, 0xA400), ("CHOICE", 0x0000, 0x0000, 0x0000, 0xA400)]
ROWS2 = [("D", "XCHOICE2_run1.out", "disk"), ("C", "XCHOICE2_run2.out", "cf3300"),
         ("N", "XCHOICE2_run3.out", "nms8250")]
BOOT = list(open(os.path.join(ROOT, "disk", "empty720.dsk"), "rb").read()[:32])   # our own generated image's sector 0
OUTPUTS = {"XH": ["a", "f", "b", "c", "de", "hl", "iff", "buf"], "XH2": ["a", "f", "b", "c", "de", "hl", "iff", "buf"]}
_NMS = ("MTOFF's registers are the INTERFACE's: on the VG-8020's NMS 1200 (XCHOICE1 run 1, XCHOICE2 run 1) always A 3, "
        "F $28, BC $0022, HL $F1C1, whatever goes in and after a read too; on the CF-3300 (run 2) A 0, F $44, BC and HL "
        "kept -- R-CH-MTOFFCF pins that row; on the NMS 8250's built-in drive (XCHOICE1 / XCHOICE2 run 3) A 3, and "
        "F, BC and HL KEPT (F $D7 out for $5AD7 in, $00 for $0000)")
UNSTABLE = {f"XH D{i:02}": (["a", "f", "b", "c", "hl"], _NMS) for i in (3, 4, 5)}
UNSTABLE.update({f"XH2 D{i:02}": (["a", "f", "b", "c", "hl"], _NMS) for i in (2, 4)})
UNSTABLE.update({f"XH2 {row}03": (["c"], "DSKIO's C after a read: XCHOICE2 run 1 (VG-8020 + NMS 1200) $22, run 2 "
                                  "(CF-3300) $3C -- a working value of each interface") for row in "DC"})
UNSTABLE.update({f"XH N{i:02}": (["a", "f", "b", "c", "hl"], _NMS) for i in (3, 4, 5)})
UNSTABLE.update({f"XH2 N{i:02}": (["a", "f", "b", "c", "hl"], _NMS) for i in (2, 4)})
UNSTABLE["XH2 N03"] = (["b", "c", "de", "hl", "iff"], "the set-up read on the NMS 8250 (XCHOICE2 run 3) leaves DE $400A and "
                       "INTERRUPTS ON (R-CH-READ: on the other two, off), C $3C as the CF-3300's -- its working "
                       "registers are the interface's")
_cache = {}


def cases():
    if "d" in _cache:
        return _cache["d"]
    d = {"ref": [], "zb": []}
    for tag, run, row in ROWS:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        sec = t[t.index(f" {row}: "):]
        sec = sec[:sec.index("\n=====")] if "\n=====" in sec else sec
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", sec).group(1))
            b += bytes(max(0, REC * len(FN) - len(b)))
            for i, (fn, bi, ci) in enumerate(FN):
                r = b[REC * i: REC * (i + 1)]
                d[who].append(NS(src="XH", id=f"XH {tag}{i:02}", row=tag, ref_only=(tag == "N"), num=i, fn=fn, bin=bi, cin=ci, a=r[0],
                                 f=r[1], b=r[2], c=r[3], de=(r[4] << 8) | r[5], hl=(r[6] << 8) | r[7], iff=r[8],
                                 buf=list(r[9:30])))
    for tag, run, row in ROWS2:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        sec = t[t.index(f" {row}: "):]
        sec = sec[:sec.index("\n=====")] if "\n=====" in sec else sec
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", sec).group(1))
            b += bytes(max(0, REC2 * len(FN2) - len(b)))
            for i, (fn, af, bc, de, hl) in enumerate(FN2):
                r = b[REC2 * i: REC2 * (i + 1)]
                d[who].append(NS(src="XH2", id=f"XH2 {tag}{i:02}", row=tag, ref_only=(tag == "N"), num=100 + i, fn=fn, afin=af, bcin=bc,
                                 dein=de, hlin=hl, a=r[0], f=r[1], b=r[2], c=r[3], de=(r[4] << 8) | r[5],
                                 hl=(r[6] << 8) | r[7], iff=r[8], buf=list(r[9:41])))
    _cache["d"] = d
    return d


def kept(c, *regs):
    got = {"af": (c.a << 8) | c.f, "bc": (c.b << 8) | c.c, "de": c.de, "hl": c.hl}
    want = {"af": c.afin, "bc": c.bcin, "de": c.dein, "hl": c.hlin}
    return all(got[r] == want[r] for r in regs)


def other_ref(c):
    """the VG-8020 + NMS 1200 for the CF-3300 and back (the NMS 8250, row N, is no one's pair)"""
    return next(o for o in cases()["ref"] if o.src == c.src and o.num == c.num and o.row != c.row and o.row != "N")


S1 = "1. CHOICE and MTOFF"
RULES = [
    Rule("R-CH-CHOICE", S1, "CHOICE ($4019) answers HL = a pointer into the disk ROM (page 1, $4000 .. $7FFF, not 0: "
         "the format-choice text, whose bytes are the ROM's own and not read here) -- the same whatever goes in, "
         "and after a read too (after MTOFF) -- and keeps AF ($5AD7 in, $5AD7 out), BC (B and C unequal too) "
         "and DE (the registers recorded). Interrupts off after the CALSLT; nothing written (the buffer at HL's entry value keeps its $E5, "
         "all 32 bytes in round 2). The pointer's value is the ROM's layout: $799B on the VG-8020's NMS 1200, $78AD "
         "on the CF-3300.", lambda c: c.fn == "CHOICE",
         lambda c: 0x4000 <= c.hl <= 0x7FFF and c.iff == 0 and (
             (c.a, c.f, c.b, c.c, c.de, c.buf) == (0, 0, c.bin, c.cin, 0, [0xE5] * 21) if c.src == "XH"
             else kept(c, "af", "bc", "de") and c.buf == [0xE5] * 32)),
    Rule("R-CH-MTOFF", S1, "MTOFF ($401F) writes nothing a program passed it (the buffer keeps its $E5), keeps DE "
         "($5678 in, out) and returns with interrupts off -- with the motor off and right after a read alike. Its "
         "A, F, BC and HL are the interface's own: the NMS 1200 answers A 3, F $28, BC $0022, HL $F1C1 whatever goes "
         "in (UNSTABLE below, by interface); the CF-3300 as R-CH-MTOFFCF.", lambda c: c.fn == "MTOFF",
         lambda c: c.iff == 0 and (c.de == 0 and c.buf == [0xE5] * 21 if c.src == "XH"
                                   else kept(c, "de") and c.buf == [0xE5] * 32)),
    Rule("R-CH-MTOFFCF", S1, "On the CF-3300 (the interface zerobas's disk ROM is) MTOFF answers A 0, F $44 and KEEPS "
         "BC and HL ($1234 / $C000 in, out).", lambda c: c.fn == "MTOFF" and c.row == "C",
         lambda c: (c.a, c.f) == (0, 0x44) and (c.b, c.c, c.hl) == (
             (c.bin, c.cin, 0xA400) if c.src == "XH" else (c.bcin >> 8, c.bcin & 0xFF, c.hlin))),
    Rule("R-CH-READ", S1, "Round 2's set-up read (DSKIO, sector 0 to $A800) moves the image's boot sector (the 32 "
         "bytes recorded), A 0, the carry clear, on all three interfaces. On the VG-8020 + NMS 1200 and the CF-3300 "
         "interrupts are off after and F, B, DE, HL are the same (zerobas differs in F and HL only); the NMS 8250 "
         "leaves interrupts ON and DE $400A (UNSTABLE below) -- a caller cannot count on DSKIO's interrupt state.",
         lambda c: c.fn == "DSKIO",
         lambda c: c.buf == BOOT and c.a == 0 and not (c.f & 1)
         and (c.row == "N" or c.iff == 0
              and (lambda o: (c.f, c.b, c.de, c.hl) == (o.f, o.b, o.de, o.hl))(other_ref(c)))),
]
