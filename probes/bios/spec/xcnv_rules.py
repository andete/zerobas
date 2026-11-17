#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CNVCHR.md's EXECUTABLE RULES (docs/spec-method.md §3a): CNVCHR ($00AB), exhaustively -- every A x GRPHED
in {0, 1, $5A} x the entry flags {$00, $FF} -- from scratchpad/XCNV_run1.out (probes/bios/spec/xcnv.asm documents the
order and the 3-byte record)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/CNVCHR.md"
OUTPUTS = {"XV": ["a_out", "f", "grphed"]}
N = 1536


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XCNV_run1.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        if b[1] != 0xA5 or len(b) < 2 + 3 * N + 1 or b[2 + 3 * N] != 0xC3:
            sys.exit("FAIL: the XCNV block is not complete (no sentinel)")
        cs = []
        for i in range(N):
            r = b[2 + 3 * i: 5 + 3 * i]
            cs.append(NS(src="XV", id=f"XV {i:04}", ef=(0x00, 0xFF)[i // 768], g=(0, 1, 0x5A)[(i // 256) % 3],
                         a=i % 256, a_out=r[0], f=r[1], grphed=r[2]))
        out[who] = cs
    return out


C, Z = 0x01, 0x40


def head(c):
    return c.g == 0 and c.a == 1


def conv(c):
    return c.g != 0 and 0x40 <= c.a <= 0x5F


S1 = "1. CNVCHR ($00AB): the graphic-character header"

RULES = [
    Rule("R-V-HEAD", S1, "With GRPHED 0, A = $01 (the graphic header) sets GRPHED to 1 and returns A as it was with the "
         "carry CLEAR (and Z set).", head,
         lambda c: c.a_out == 1 and c.grphed == 1 and c.f & (C | Z) == Z),
    Rule("R-V-CONV", S1, "With GRPHED set -- 1 or any non-zero value ($5A) -- A from $40 to $5F becomes A − $40 (the "
         "graphic character) with the carry SET and Z CLEAR, and GRPHED becomes 0.", conv,
         lambda c: c.a_out == c.a - 0x40 and c.grphed == 0 and c.f & (C | Z) == C),
    Rule("R-V-PASS", S1, "Every other A comes back unchanged with the carry SET and Z SET, and GRPHED becomes 0: the "
         "rest of the 256 values after the header, a second $01 after the header included, and every value but $01 "
         "with GRPHED 0.", lambda c: not head(c) and not conv(c),
         lambda c: c.a_out == c.a and c.grphed == 0 and c.f & (C | Z) == C | Z),
    Rule("R-V-F", S1, "The whole F on return (only C and Z published): 42 after the header, A3 after a conversion, "
         "41 OR (A AND $28) -- A's bits 5 and 3 copied -- otherwise; the flags on entry ($00 / $FF) never matter.",
         lambda c: True,
         lambda c: c.f == (0x42 if head(c) else 0xA3 if conv(c) else 0x41 | (c.a & 0x28))),
]


# ---- round 2: XCNV2 (probes/bios/spec/xcnv2_cases.py; scratchpad/XCNV2_run1.out), after the first review
sys.path.insert(0, HERE)
import xcnv2_cases as X2  # noqa: E402

OUTPUTS["XV2"] = ["a_out", "f", "bc", "de", "hl", "ix", "iy", "grphed", "hlbyte", "iff", "nchg", "first"]
_cases1 = cases


def cases():                                     # noqa: F811
    out = _cases1()
    t = open(os.path.join(ROOT, "scratchpad", "XCNV2_run2.out")).read()
    for who, key in (("ref", "ref"), ("zb", "ours")):
        for c in X2.decode(bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))):
            c.src, c.id, c.f = "XV2", f"XV2 {c.idx:02}", c.f_out
            out[who].append(c)
    return out


def _cls(a, g):
    return "head" if g == 0 and a == 1 else "conv" if g != 0 and 0x40 <= a <= 0x5F else "pass"


def _expect(a, g):
    k = _cls(a, g)
    return {"head": (1, 1, 0x42), "conv": (a - 0x40, 0, 0xA3), "pass": (a, 0, 0x41 | (a & 0x28))}[k]


def _first_ok(c):
    """A seq case's first call: the header from GRPHED 0."""
    if not c.seq:
        return c.first is None
    f = c.first
    return ((f["a_out"], f["grphed"], f["f_out"]) == (1, 1, 0x42) and f["hlbyte"] == 1
            and (f["bc"], f["de"], f["hl"], f["ix"], f["iy"], f["iff"], f["nchg"]) == (0x1357, 0x9BDF, 0xEF10, 0x4321,
                                                                                        0x8765, 0, 0))


for _r in RULES:
    _r.select = (lambda s: (lambda c: c.src == "XV" and s(c)))(_r.select)

S2 = "2. Round 2: every register garbage, more GRPHED and entry-flag values, the natural sequence (XCNV2)"

RULES += [
    Rule("R-V-ANYG", S2, "GRPHED counts as set for ANY non-zero value -- $80, $FF, $20, $04 (bits 7, 5, 2 alone) as "
         "well as 1 and $5A -- and every call but the header leaves it 0. A, GRPHED and the whole F follow R-V-HEAD / "
         "R-V-CONV / R-V-PASS / R-V-F whatever the flags on entry ($01, $40, $41, $80, $04, $10, $55, $AA too).",
         lambda c: c.src == "XV2" and not c.seq,
         lambda c: c.first is None and (c.a_out, c.grphed, c.f) == _expect(c.a, c.g)),
    Rule("R-V-SEQ", S2, "The natural sequence works with GRPHED left by the routine itself: CNVCHR($01) from GRPHED 0 "
         "arms it, then CNVCHR($40) gives 00, ($5F) 1F; ($3F), ($60) and a second ($01) pass unchanged with C and Z "
         "set -- and leave GRPHED 0.", lambda c: c.src == "XV2" and c.seq,
         lambda c: _first_ok(c) and (c.a_out, c.grphed, c.f) == _expect(c.a, 1)),
    Rule("R-V-REGS", S2, "It tests GRPHED itself: HL pointed at a byte holding the OPPOSITE of GRPHED's zero-ness and "
         "D never equalled A, and the results follow GRPHED and A; that byte is not written. BC, DE, HL, IX and IY "
         "are kept, interrupts stay disabled, and no other cell of the work area $F380-$FFFF changes.",
         lambda c: c.src == "XV2",
         lambda c: ((c.bc, c.de, c.hl, c.ix, c.iy, c.iff, c.nchg) == (0x1357, 0x9BDF, 0xEF10, 0x4321, 0x8765, 0, 0)
                    and c.hlbyte == (1 if c.g == 0 and not c.seq else 0))),
]
