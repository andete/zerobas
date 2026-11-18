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


# ---- round 2: XFNK3 (probes/bios/spec/xfnk3.asm; scratchpad/XFNK3_run2.out, both rows) and XFNK's boot-time FNKSTR
OUTPUTS["XF3"] = ["fnk", "a", "f", "bc", "de", "hl", "ix", "iy", "iff", "row24", "nchg", "chg"]
OUTPUTS["XB"] = ["boot"]
ENTRY_AF = [(0xA5, 0x00), (0x00, 0xFF), (0x5A, 0xFF)]
REF_F3 = {0: 0x00, 1: 0xC1, 2: 0xE9}            # F on return, the reference's (per case)
# run 1 compared the work area AFTER the probe's own VRAM reads (RDVRM let an interrupt run) and saw the timer cells
# $F3F6, $FC9E, $FCA2; run 2 compares right after the call: the reference changes none

_cases1 = cases


def cases():                                     # noqa: F811
    out = _cases1()
    t = open(os.path.join(ROOT, "scratchpad", "XFNK3_run2.out")).read()
    caps = re.findall(r"CAP (ref|ours)\s*:\s*([0-9a-fA-F]+)", t)
    if len(caps) != 4:
        sys.exit("FAIL: XFNK3 needs both rows (nodisk, disk)")
    for n, (who, h) in enumerate(caps):
        b = bytes.fromhex(h)
        row = ("nodisk", "disk")[n // 2]
        for k in range(3):
            r = b[2 + 236 * k: 2 + 236 * (k + 1)]
            if b[1] != 0xA5 or r[235] != 0xC3:
                sys.exit("FAIL: an XFNK3 record has no sentinel")
            w = lambda j: (r[j] << 8) | r[j + 1]                     # noqa: E731
            cnt = r[213] | (r[214] << 8)
            out["ref" if who == "ref" else "zb"].append(NS(
                src="XF3", id=f"XF3 {row} {k + 1}", case=k, row=row, fnk=list(r[:160]), a=r[160], f=r[161],
                bc=w(162), de=w(164), hl=w(166), ix=w(168), iy=w(170), iff=(r[172] >> 2) & 1, row24=list(r[173:213]),
                nchg=cnt, chg=[r[215 + 2 * i] | (r[216 + 2 * i] << 8) for i in range(min(cnt, 10))]))
    # D-FNKBOOT (2026-11-18): the fixed build's run (run 1 was zerobas empty, the reference the same)
    t = open(os.path.join(ROOT, "scratchpad", "XFNK_fix1.out")).read()
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        out[who].append(NS(src="XB", id="XB 1", boot=list(b[1:161])))
    return out


def r2(c):
    return c.src == "XF3"


for _r in RULES:
    _r.select = (lambda s: (lambda c: c.src == "XF" and s(c)))(_r.select)

S2 = "2. Round 2: several inputs, everything else read (XFNK3)"
S3 = "3. At cartridge INIT"
DEFBYTES = [x for d in DEFAULTS for x in (d + bytes(16))[:16]]

RULES += [
    Rule("R-F-ALL", S2, "From ANY start -- all $00, all $5A, or per key $00 / $5A / 16 letters with no 0 / the "
         "default 'list ' with $5A padding -- all 160 bytes end as R-F-DEFAULTS states: whole 16-byte slots are "
         "written, the padding zeros included. On the diskless and the disk machine alike.", r2,
         lambda c: c.fnk == DEFBYTES),
    Rule("R-F-REGS", S2, "A is kept ($A5, $00, $5A in); IX / IY are kept; BC returns 0000, DE $F91F (just past "
         "FNKSTR) and HL $1449; of F, S / Z / C come through from entry and H / P/V / N are cleared (measured 00 "
         "from $00, C1 and E9 from $FF).", r2,
         lambda c: ((c.a, c.f) == (ENTRY_AF[c.case][0], REF_F3[c.case])
                    and (c.bc, c.de, c.hl, c.ix, c.iy) == (0, 0xF91F, 0x1449, 0x4321, 0x8765))),
    Rule("R-F-DI", S2, "Entered with interrupts disabled, it returns with them disabled.", r2, lambda c: c.iff == 0),
    Rule("R-F-NOREDRAW", S2, "It does not redraw the key line, also with CNSDFG $FF: row 24 keeps its $5A.", r2,
         lambda c: c.row24 == [0x5A] * 40),
    Rule("R-F-WAREA", S2, "Outside FNKSTR NOTHING in the whole work area $F380-$FFFF changes: compared right after the "
         "call, before any other BIOS call (run 2; run 1's timer cells were the probe's own interrupt, let in by its "
         "VRAM reads).", r2, lambda c: c.nchg == 0 and c.chg == []),
    Rule("R-F-BOOT", S3, "When a cartridge's INIT runs, FNKSTR already holds the ten defaults (XFNK, zerobas's side re-run on the 2026-11-18 build).",
         lambda c: c.src == "XB", lambda c: c.boot == DEFBYTES),
]
