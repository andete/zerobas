#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
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
ROWS = [("D", "XCHOICE1_run1.out", "disk"), ("C", "XCHOICE1_run2.out", "cf3300")]
OUTPUTS = {"XH": ["a", "f", "b", "c", "de", "hl", "iff", "buf"]}
UNSTABLE = {f"XH {row}{i:02}": (["a", "f", "b", "c", "hl"], "MTOFF's registers depend on the interface: XCHOICE1 run 1 "
                                "(VG-8020 + NMS 1200) answers A 3, F $28, BC $0022, HL $F1C1 whatever goes in; run 2 "
                                "(CF-3300) A 0, F $44, BC and HL as entered") for row in "DC" for i in (3, 4, 5)}
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
                d[who].append(NS(src="XH", id=f"XH {tag}{i:02}", row=tag, num=i, fn=fn, bin=bi, cin=ci, a=r[0],
                                 f=r[1], b=r[2], c=r[3], de=(r[4] << 8) | r[5], hl=(r[6] << 8) | r[7], iff=r[8],
                                 buf=list(r[9:30])))
    _cache["d"] = d
    return d


S1 = "1. CHOICE and MTOFF"
RULES = [
    Rule("R-CH-CHOICE", S1, "CHOICE ($4019) answers HL = a pointer into the disk ROM (page 1, $4000 .. $7FFF, not 0: "
         "the format-choice text, whose bytes are the ROM's own and not read here) -- the same whatever B and C are "
         "-- with A 0, F 0, B, C and DE as entered, interrupts off after the CALSLT, and nothing written (the buffer "
         "at HL's entry value keeps its $E5). The pointer's value is the ROM's layout: $799B on the VG-8020's NMS "
         "1200, $78AD on the CF-3300.", lambda c: c.fn == "CHOICE",
         lambda c: 0x4000 <= c.hl <= 0x7FFF and (c.a, c.f, c.b, c.c, c.de, c.iff) == (0, 0, c.bin, c.cin, 0, 0)
         and c.buf == [0xE5] * 21),
    Rule("R-CH-MTOFF", S1, "MTOFF ($401F) writes nothing a program passed it (the buffer keeps its $E5), keeps DE and "
         "returns with interrupts off; its A, F, BC and HL are the interface's own (UNSTABLE below: the NMS 1200 "
         "answers A 3 / F $28 / BC $0022 / HL $F1C1, the CF-3300 keeps BC and HL).", lambda c: c.fn == "MTOFF",
         lambda c: c.de == 0 and c.iff == 0 and c.buf == [0xE5] * 21),
]
