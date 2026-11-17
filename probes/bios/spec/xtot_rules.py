#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/TOTEXT.md's EXECUTABLE RULES (docs/spec-method.md §3a): TOTEXT ($00D2), from the XTOT matrix --
scratchpad/XTOT_run1.out. The case list, the setup and the record are in xtot_cases.py."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import xtot_cases as X  # noqa: E402
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/TOTEXT.md"
GB = 0x5A
OUTPUTS = {"XT": ["rg", "scrmod", "oldscr", "linlen", "crtcnt", "csrx", "csry", "cnsdfg", "sum40", "sum32", "vsum"]}
# the register copies each mode's call leaves (INITXT / INIT32 / INIGRP / INIMLT, from SCREEN 0's), as the reference
# left them on entry to TOTEXT -- and after it
RG = {0: [0x00, 0xF0, 0x00, 0x00, 0x01, 0x00, 0x00, 0xF4], 1: [0x00, 0xE0, 0x06, 0x80, 0x00, 0x36, 0x07, 0x04],
      3: [0x00, 0xE8, 0x02, 0x00, 0x00, 0x36, 0x07, 0x04]}
# the reference's VRAM sums after a mode change (the font and the boot-time key labels included: literal), per
# (OLDSCR, CNSDFG on entry): (sum of $0000-$03BF, sum of $1800-$1AFF, sum of all 16 KB)
VREF = {(0, 0): (30720, 3584, 20751), (0, 1): (32290, 3584, 22321), (1, 0): (7280, 24576, 35839),
        (1, 1): (7280, 26146, 37409), (0x5A, 0): (65280, 3584, 2224), (0x5A, 1): (65280, 3584, 2224)}


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XTOT_run1.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        cs = X.decode(bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1)))
        for c in cs:
            c.src, c.id = "XT", f"XT {c.idx:02}"
        out[who] = cs
    return out


def grp(c):
    return c.mode >= 2


S1 = "1. TOTEXT ($00D2): back to a text screen"

RULES = [
    Rule("R-T-TEXT", S1, "In SCREEN 0 or 1 TOTEXT does nothing: the register copies, SCRMOD, OLDSCR (0, 1 or "
         "garbage), LINLEN, the cursor, CNSDFG and every VRAM byte stay as found.", lambda c: not grp(c),
         lambda c: (c.rg == RG[c.mode] and (c.scrmod, c.oldscr, c.linlen) == (c.mode, c.old, 40 if c.mode == 0 else 32)
                    and (c.csrx, c.csry, c.cnsdfg) == (7, 5, c.cns)
                    and (c.sum40, c.sum32, c.vsum) == ((GB * 960) & 0xFFFF, (GB * 768) & 0xFFFF,
                                                       (GB * 16384) & 0xFFFF))),
    Rule("R-T-OLD0", S1, "In SCREEN 2 or 3 with OLDSCR 0 it is INITXT (docs/bios/INITXT.md): SCREEN 0, LINLEN := "
         "LINL40 (37), the cursor home, CNSDFG 255 when it was on, INITXT's registers -- every VRAM sum the "
         "reference's.", lambda c: grp(c) and c.old == 0,
         lambda c: (c.rg == RG[0] and (c.scrmod, c.oldscr, c.linlen) == (0, 0, 37)
                    and (c.csrx, c.csry, c.cnsdfg) == (1, 1, 255 if c.cns else 0)
                    and (c.sum40, c.sum32, c.vsum) == VREF[(0, c.cns)])),
    Rule("R-T-OLD1", S1, "With OLDSCR 1 it is INIT32: SCREEN 1, LINLEN := LINL32 (29), the cursor home, CNSDFG 255 "
         "when it was on, INIT32's registers -- every VRAM sum the reference's.", lambda c: grp(c) and c.old == 1,
         lambda c: (c.rg == RG[1] and (c.scrmod, c.oldscr, c.linlen) == (1, 1, 29)
                    and (c.csrx, c.csry, c.cnsdfg) == (1, 1, 255 if c.cns else 0)
                    and (c.sum40, c.sum32, c.vsum) == VREF[(1, c.cns)])),
    Rule("R-T-OLDX", S1, "With a garbage OLDSCR ($5A) the reference sets up SCREEN 3 (the multicolour registers, "
         "SCRMOD 3; OLDSCR, the cursor and CNSDFG left as found), from SCREEN 2 and 3 alike -- not a text screen.",
         lambda c: grp(c) and c.old == 0x5A,
         lambda c: (c.rg == RG[3] and (c.scrmod, c.oldscr) == (3, 0x5A) and (c.csrx, c.csry, c.cnsdfg) == (7, 5, c.cns)
                    and (c.sum40, c.sum32, c.vsum) == VREF[(0x5A, c.cns)])),
    Rule("R-T-CRTCNT", S1, "CRTCNT is never changed (24).", lambda c: True, lambda c: c.crtcnt == 24),
]

UNREAD = {f"XT {i:02}": (["linlen"], "garbage-OLDSCR cases: the reference's SCREEN 3 set-up leaves LINLEN, so its "
                                    "value is the previous case's")
          for i, c in enumerate(X.CASES) if c.mode >= 2 and c.old == 0x5A}


# ---- round 2: XTOT2 (probes/bios/spec/xtot2_cases.py; scratchpad/XTOT2_run1.out), after the first review
import xtot2_cases as X2  # noqa: E402

OUTPUTS["XT2"] = ["rg", "scrmod", "oldscr", "linlen", "crtcnt", "csrx", "csry", "cnsdfg", "keyrow", "vsum"]
BOOTKEYS = [b"color ", b"auto ", b"goto ", b"list ", b"run\r"]      # FNKSTR's first five as the boot leaves them
# the reference's whole-VRAM sums per case (the font included -- ruled, D-BIOSINT; INIT32's also hold the colour and
# sprite tables, which follow the colours and the sprite size)
VREF2 = {0: 20751, 1: 32768, 2: 22321, 3: 37409, 4: 22321, 5: 22321, 6: 20751, 7: 29503, 8: 20751, 9: 37327,
         10: 3712, 11: 29312, 12: 3712, 13: 3712, 14: 3712, 15: 20751, 16: 20751}


def _cases_r2():
    t = open(os.path.join(ROOT, "scratchpad", "XTOT2_run1.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        cs = X2.decode(bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1)))
        for c in cs:
            c.src, c.id = "XT2", f"XT2 {c.idx:02}"
        out[who] = cs
    return out


_cases1 = cases


def cases():                                     # noqa: F811
    out, r2 = _cases1(), _cases_r2()
    return {w: out[w] + r2[w] for w in out}


def target(c):
    """The screen TOTEXT sets up for a case whose SCRMOD is 2 or 3: OLDSCR 0, $81, $FF -> 0 (OLDSCR := 0); 1 -> 1;
    2 -> 2; 3, $5A, $7F, $80 -> 3 -- the measured values."""
    return {0: 0, 1: 1, 2: 2}.get(c.old, 0 if c.old in (0x81, 0xFF) else 3)


def entry_scr(c):
    return c.scr if c.scr != 0xFF else c.mode


def key_cells(width, cols):
    m, slot = (cols - width + 1) // 2, (width + 1) // 5
    row = [32] * cols
    for k in range(5):
        for j, ch in enumerate(list(BOOTKEYS[k].rstrip(b"\r"))[:slot - 1]):
            row[m + k * slot + j] = ch
    return row


def t2_expect(c):
    """XTOT2's outputs from the case's inputs, as the rules state them."""
    s = entry_scr(c)
    rg0_in = c.rg0 if c.rg0 != 0xFF else (0x00 if c.mode < 2 else 0x02)
    rg1_in = c.rg1 if c.rg1 != 0xFF else {0: 0xF0, 1: 0xE0, 2: 0xE0, 3: 0xE8}[c.mode]
    if s < 2:                                    # nothing at all
        return dict(scrmod=s, oldscr=c.old, linlen=50, csrx=7, csry=5, cnsdfg=c.cns, keyrow=[0x5A] * 12)
    t = target(c)
    e = dict(scrmod=t, oldscr=(t if c.old in (0x81, 0xFF) else c.old), crtcnt=c.crt)
    if t == 0:
        e.update(linlen=37, csrx=1, csry=1, cnsdfg=255 if c.cns else 0,
                 rg=[rg0_in & 1, (rg1_in & 0xA7) | 0x50, 0, 0, 1, 0, 0, ((c.fg << 4) | c.bg) & 0xFF],
                 keyrow=(key_cells(37, 40) if c.cns else [32] * 40)[:12])
    elif t == 1:
        e.update(linlen=29, csrx=1, csry=1, cnsdfg=255 if c.cns else 0,
                 rg=[rg0_in & 1, (rg1_in & 0xA7) | 0x40, 6, 0x80, 0, 0x36, 7, c.bd],
                 keyrow=(key_cells(29, 32) if c.cns else [32] * 32)[:12])
    else:                                        # back to a graphics screen: no cursor home, LINLEN kept
        e.update(linlen=50, csrx=7, csry=5, cnsdfg=c.cns,
                 keyrow=[0x00] * 12 if t == 2 else [((c.bg & 15) * 17)] * 12)   # INIGRP's cleared patterns /
        # INIMLT's BAKCLR in both nibbles (BAKCLR 4: $44) where the row read lands
    return e


def t2_ok(c, fields):
    """With the entry copies set by the case (rg0 / rg1), R0 / R1 are checked whole; otherwise -- the copies as the
    mode's call left them, which keeps bits from the PREVIOUS case's copies, not recorded -- only the bits TOTEXT's
    INITXT / INIT32 force: R0's bits 1-7 clear, R1's bits 6 / 4 / 3 as forced, and R2..R7 whole."""
    e = t2_expect(c)
    ok = all(getattr(c, f) == e[f] for f in fields if f in e and f != "rg")
    if "rg" in fields and "rg" in e:
        if c.rg0 != 0xFF:
            ok = ok and c.rg == e["rg"]
        else:
            ok = ok and c.rg[0] & 0xFE == 0 and c.rg[1] & 0x58 == e["rg"][1] & 0x58 and c.rg[2:] == e["rg"][2:]
    return ok


for _r in RULES:
    _r.select = (lambda s: (lambda c: c.src == "XT" and s(c)))(_r.select)

S2 = "2. Round 2: SCRMOD, OLDSCR, the copies, CRTCNT, CNSDFG, the colours at several values (XTOT2)"
_ALL2 = ["scrmod", "oldscr", "linlen", "csrx", "csry", "cnsdfg", "keyrow"]

RULES += [
    Rule("R-T-SCRMOD", S2, "SCRMOD decides, not the register copies: INITXT's copies with SCRMOD 2 are acted on (INITXT); "
         "INIGRP's copies with SCRMOD 0 are left alone (nothing at all, LINLEN's 50 kept).",
         lambda c: c.src == "XT2" and c.scr != 0xFF, lambda c: t2_ok(c, _ALL2 + ["crtcnt", "rg"])),
    Rule("R-T-DISPATCH", S2, "OLDSCR is a dispatch, not a text choice: 0, $81 and $FF set up SCREEN 0 (and OLDSCR "
         "becomes 0); 1 SCREEN 1; 2 SCREEN 2 -- back to the graphics screen; 3, $5A, $7F and $80 SCREEN 3. The graphics "
         "outcomes leave LINLEN (50), the cursor and CNSDFG as found.",
         lambda c: c.src == "XT2" and c.old not in (0, 1), lambda c: t2_ok(c, _ALL2 + ["crtcnt", "rg"])),
    Rule("R-T-THRU", S2, "TOTEXT's INITXT / INIT32 follow INITXT's page with the inputs as found: CRTCNT 13 kept and "
         "the key line on row 13 (the boot's labels: '  color  aut' / '  color auto'); CNSDFG $80 / $FF become 255; "
         "R7 from the colours (3A, 09); RG0SAV $03 / RG1SAV $E3 give R0 01 and R1 F3 / E3 -- the register copies as "
         "INITXT.md's R0 and register rules compute them (whole where the case set the entry copies; where the mode's "
         "call left them, from bits of the previous case's, only the bits TOTEXT forces and R2-R7).",
         lambda c: c.src == "XT2" and c.scr == 0xFF and c.old in (0, 1),
         lambda c: t2_ok(c, _ALL2 + ["crtcnt", "rg"])),
    Rule("R-T-VRAM2", S2, "The whole VRAM's sum is the reference's, per case (the font included: ruled; INIT32's sum "
         "also follows the colours and the sprite size; INITXT's does not: the colours 3, 10, 9 give the same sum).",
         lambda c: c.src == "XT2",
         lambda c: c.vsum == VREF2[c.idx]),
    Rule("R-T-REGS2", S2, "The register copies after the graphics outcomes are the reference's (INIGRP's / INIMLT's, "
         "the entry bits kept: 03 E3 06 FF 03 36 07 04 for SCREEN 2, 01 EB 02 00 00 36 07 04 for SCREEN 3); with "
         "nothing done they stay as found.",
         lambda c: c.src == "XT2" and (entry_scr(c) < 2 or target(c) >= 2),
         lambda c: c.rg == ([0x02, 0xE0, 0x06, 0xFF, 0x03, 0x36, 0x07, 0x04] if entry_scr(c) < 2 else
                            [0x03, 0xE3, 0x06, 0xFF, 0x03, 0x36, 0x07, 0x04] if target(c) == 2 else
                            [0x01, 0xEB, 0x02, 0x00, 0x00, 0x36, 0x07, 0x04]) and c.crtcnt == c.crt),
]
