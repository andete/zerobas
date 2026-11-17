#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/INIFNK.md's EXECUTABLE RULES (docs/spec-method.md §3a): INIFNK ($003E) from garbage, from the XFNK2 probe --
scratchpad/XFNK2_run1.out (probes/bios/spec/xfnk2.asm documents the setup and the capture)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/INIFNK.md"
OUTPUTS = {"XF": ["fnk", "before", "after", "a", "f"]}
# the ten default strings, each padded with 0 to 16 bytes (as the page states them)
DEFAULTS = [b"color ", b"auto ", b"goto ", b"list ", b"run\r", b"color 15,4,4\r", b'cload"', b"cont\r",
            b"list.\r\x1e\x1e", b"\x0crun\r"]


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XFNK2_run1.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        if b[1] != 0xA5 or b[166] != 0xC3:
            sys.exit("FAIL: the XFNK2 block is not complete (no sentinel)")
        out[who] = [NS(src="XF", id="XF 1", fnk=list(b[2:162]), before=b[162], after=b[163], a=b[164], f=b[165])]
    return out


S1 = "1. INIFNK ($003E): the default function-key strings"

RULES = [
    Rule("R-F-DEFAULTS", S1, "INIFNK writes all 160 bytes of FNKSTR (from $5A garbage): the ten default strings -- "
         "'color ', 'auto ', 'goto ', 'list ', 'run' CR, 'color 15,4,4' CR, 'cload\"', 'cont' CR, 'list.' CR + two "
         "$1E (cursor up), $0C (CLS) + 'run' CR -- each padded with 0 to its 16 bytes.", lambda c: True,
         lambda c: c.fnk == [x for d in DEFAULTS for x in (d + bytes(16))[:16]]),
    Rule("R-F-BOUNDS", S1, "Nothing outside FNKSTR: the bytes just before and after it keep their $A5.",
         lambda c: True, lambda c: (c.before, c.after) == (0xA5, 0xA5)),
    Rule("R-F-AF", S1, "A is kept ($5A on entry, $5A on return); F on return (not published): E9.", lambda c: True,
         lambda c: (c.a, c.f) == (0x5A, 0xE9)),
]
