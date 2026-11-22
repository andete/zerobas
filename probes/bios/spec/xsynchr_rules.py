#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/SYNCHR.md's EXECUTABLE RULES (docs/spec-method.md §3a): SYNCHR ($0008) on its match path for every byte
value in two passes -- scratchpad/XSYNCHR_run1.out (probes/bios/spec/xsynchr.asm) -- and on its mismatch path, caught
at the error hook H.ERRO -- scratchpad/XSYNCHR2_run1.out (probes/bios/spec/xsynchr2.asm)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
from xchrgtr_rules import plain  # noqa: E402

PAGE = "docs/bios/SYNCHR.md"
OUTPUTS = {"XS": ["a", "f", "hl", "kept", "ret"], "XS2": ["path", "e", "a", "hl"]}
# per pass of XSYNCHR: what CHRGTR finds after the matched byte (A, offset of HL from the text)
AFTER = [(0x31, 1), (0x41, 2)]


def block(name, key, n, size):
    t = open(os.path.join(ROOT, "scratchpad", name)).read()
    b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
    if b[0] != 0xA5 or len(b) < 2 + size * n or b[1 + size * n] != 0xC3:
        sys.exit(f"FAIL: the {name} block is not complete (no sentinel)")
    return [b[1 + size * i:1 + size * (i + 1)] for i in range(n)]


def cases():
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        out[who] = [NS(src="XS", id=f"XS {i >> 8}.{i & 0xFF:02X}", p=i >> 8, c=i & 0xFF, a=r[0], f=r[1],
                       hl=r[2] | r[3] << 8, kept=r[4], ret=r[5])
                    for i, r in enumerate(block("XSYNCHR_run1.out", key, 512, 6))]
        out[who] += [NS(src="XS2", id=f"XS2 {i:03}", i=i, path=r[0], e=r[1], a=r[2], hl=r[3])
                     for i, r in enumerate(block("XSYNCHR2_run1.out", key, 259, 4))]
    return out


S1 = "1. SYNCHR ($0008, RST 08h): check the byte at HL against the byte after the RST"
XS = lambda c: c.src == "XS"  # noqa: E731
XS2 = lambda c: c.src == "XS2"  # noqa: E731

RULES = [
    Rule("R-S-MATCH", S1, "When the byte at HL equals the byte after the `RST 08h` (every byte value 0-255, tokens "
         "included), SYNCHR returns to the instruction after that byte.", XS, lambda c: c.ret == 0x5C),
    Rule("R-S-NEXT", S1, "It then does what CHRGTR does from the matched byte: HL on the next character, spaces "
         "skipped, A that character and CHRGTR's F (pass 0: '1' right after, HL + 1; pass 1: a space then 'A', HL + "
         "2) -- whatever A and F were on entry ($A7 / $00, $00 / $FF).", XS,
         lambda c: (c.a, c.hl) == AFTER[c.p] and c.f == plain(c.a)),
    Rule("R-S-KEPT", S1, "BC, DE, IX and IY are kept -- two sets of values, the second every marker complemented.",
         XS, lambda c: c.kept == 0),
    Rule("R-S-MISS", S1, "When they differ (every byte value at HL against that value XOR 1), SYNCHR does not return: "
         "it raises Syntax error -- the error hook H.ERRO ($FFB1) is called with E = 2.",
         lambda c: XS2(c) and c.i < 256, lambda c: (c.path, c.e) == (0xE7, 2)),
    Rule("R-S-NOSKIP", S1, "The byte at HL is compared as it stands: a space or a TAB in front of the expected byte "
         "is a mismatch (Syntax error), not skipped.", lambda c: XS2(c) and c.i in (256, 257),
         lambda c: (c.path, c.e) == (0xE7, 2)),
    Rule("R-S-CTRL", S1, "With the hook in place a match still returns (',' against ','; HL + 1, A '1'): the hook "
         "fires on the mismatch alone.", lambda c: XS2(c) and c.i == 258,
         lambda c: (c.path, c.e, c.a, c.hl) == (0x5C, 0, 0x31, 1)),
]

UNREAD = {f"XS2 {i:03}": (["a", "hl"], "the hook ran: the probe writes 0 into both bytes itself (the error path has no "
                          "return values to read)") for i in range(258)}
