#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/GETYPR.md's EXECUTABLE RULES (docs/spec-method.md §3a): GETYPR ($0028) for every VALTYP value, with entry
F $00 / $FF and entry A $A7 / $00 / $FF -- scratchpad/XGETYPR_run3.out (probes/bios/spec/xgetypr.asm documents the order and the 4-byte record)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/GETYPR.md"
OUTPUTS = {"XG": ["a", "f", "kept", "vt_out"]}
# the probe's four passes: entry F, entry A, the register markers' XOR ($FF = every marker complemented)
PASSES = [(0x00, 0xA7, 0x00), (0xFF, 0xA7, 0x00), (0x00, 0x00, 0xFF), (0xFF, 0xFF, 0xFF)]


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XGETYPR_run3.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        if b[0] != 0xA5 or len(b) < 2 + 4 * 1024 or b[1 + 4 * 1024] != 0xC3:
            sys.exit("FAIL: the XGETYPR block is not complete (no sentinel)")
        out[who] = [NS(src="XG", id=f"XG {i:04}", vt=i & 0xFF, ef=PASSES[i >> 8][0], ea=PASSES[i >> 8][1],
                       mx=PASSES[i >> 8][2], a=b[1 + 4 * i], f=b[2 + 4 * i], kept=b[3 + 4 * i], vt_out=b[4 + 4 * i])
                    for i in range(1024)]
    return out


def model(vt):
    a = (vt - 3) & 0xFF
    f = ((a & 0x80) | (0x40 if a == 0 else 0) | (a & 0x28) | (0x04 if bin(a).count("1") % 2 == 0 else 0)
         | (0x01 if vt < 8 else 0))
    return a, f


S1 = "1. GETYPR ($0028, RST 28h): the type of the value in DAC, from VALTYP ($F663)"

RULES = [
    Rule("R-G-TYPES", S1, "The four types: integer (VALTYP 2) gives S set; string (3) Z set; single (4) the carry set "
         "with S and Z clear; double (8) the carry clear.", lambda c: c.vt in (2, 3, 4, 8),
         lambda c: {2: (c.f & 0x80) != 0, 3: (c.f & 0x40) != 0, 4: (c.f & 0xC1) == 0x01, 8: (c.f & 0x01) == 0}[c.vt]),
    Rule("R-G-A", S1, "A (not published) is VALTYP − 3, for every VALTYP value 0-255, whatever A was on entry ($A7, "
         "$00, $FF).", lambda c: True,
         lambda c: c.a == model(c.vt)[0]),
    Rule("R-G-F", S1, "The whole F is a logical result's on that A -- S, Z and bits 5 / 3 from A, H and N clear, P/V "
         "set when A has an even number of 1 bits -- with the carry set exactly when VALTYP < 8; whatever F was on "
         "entry ($00 / $FF).", lambda c: True, lambda c: c.f == model(c.vt)[1]),
    Rule("R-G-KEPT", S1, "BC, DE, HL, IX and IY are kept -- two sets of values, the second every marker "
         "complemented -- and VALTYP is not changed.", lambda c: True,
         lambda c: c.kept == 0 and c.vt_out == c.vt),
]
