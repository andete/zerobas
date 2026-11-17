#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CHGET.md's EXECUTABLE RULES (docs/spec-method.md §3a): CHGET ($009F) and CHSNS ($009C) with the key buffer
filled by the probe, from the XCHG matrix -- scratchpad/XCHG_run1.out (the case list, the setup and the record are in
xchg_cases.py); and CHGET WAITING on an empty buffer for a typed key, from the keyed probe xchgw.asm --
scratchpad/XCHGW_run1.out (its header documents the two cases and the record)."""
from types import SimpleNamespace as NS
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import xchg_cases as X  # noqa: E402
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/CHGET.md"
GB, KB_GB = 0x5A, 0x66                  # the VRAM garbage; the key buffer's garbage
KEYBUF = X.KEYBUF
OUTPUTS = {"XG": ["a", "f", "getpnt", "putpnt", "iff", "csrx", "csry", "csrsw_out", "scrmod", "cnsdfg", "bufsum",
                  "vsum", "cur", "cur2"],
           "XW": ["stage", "a", "f", "iff", "getlo", "putlo", "csrsw_out", "cur", "cur2"]}
# CHGET's flags on return (not published), the reference's literal values per (GETPNT offset, codes in the buffer)
CHGET_F = {(0, 1): 0x9A, (39, 1): 0x4A, (39, 2): 0x4A, (10, 3): 0x8A}


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XCHG_run1.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        cs = X.decode(bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1)))
        for c in cs:
            c.src, c.id = "XG", f"XG {c.idx:02}"
        out[who] = cs + waited(who)
    return out


def waited(who):
    """XCHGW's two cases: CHGET on an empty buffer, entered with interrupts on (1, 'Q' typed) / off (2, 'R')."""
    t = open(os.path.join(ROOT, "scratchpad", "XCHGW_run1.out")).read()
    b = bytes.fromhex(re.search(rf"CAP {'ref' if who == 'ref' else 'ours'}\s*:\s*([0-9a-fA-F]+)", t).group(1))
    out = []
    for i, (ei, key) in enumerate(((1, ord("Q")), (0, ord("R")))):
        r = b[1 + 8 * i: 9 + 8 * i]
        out.append(NS(src="XW", id=f"XW {i + 1}", name="CHGET-WAIT", ei=ei, key=key, stage=b[0], a=r[0], f=r[1],
                      iff=(r[2] >> 2) & 1, getlo=r[3], putlo=r[4], csrsw_out=r[5], cur=r[6], cur2=r[7]))
    return out


def sub_flags(x, y):
    """The Z80's flags after the 8-bit SUB x - y."""
    r = (x - y) & 0xFF
    return ((r & 0x80) | (0x40 if r == 0 else 0) | (r & 0x28) | (0x10 if (x & 15) < (y & 15) else 0)
            | (0x04 if (x ^ y) & (x ^ r) & 0x80 else 0) | 0x02 | (0x01 if x < y else 0))


def buf_sum(c):
    buf = [KB_GB] * 40
    for k in range(c.n):
        buf[(c.off + k) % 40] = c.codes[k]
    return sum(buf) & 0xFFFF


def quiet(c):
    """Nothing but the key buffer's pointers: VRAM (cursor cell included), the cursor, CSRSW, SCRMOD, CNSDFG, the
    buffer's bytes as found."""
    return (c.vsum == (GB * 16384) & 0xFFFF and (c.cur, c.cur2) == (GB, GB) and (c.csrx, c.csry) == (7, 5)
            and c.csrsw_out == c.csrsw and c.scrmod == (0 if c.mode == 0 else 2) and c.cnsdfg == 0
            and c.bufsum == buf_sum(c))


def chget(c):
    return c.name == "CHGET"


def wait(c):
    return c.name == "CHGET-WAIT"


S1, S2 = "1. CHGET ($009F): take a code from the key buffer", "2. CHSNS ($009C): is there a code?"

RULES = [
    Rule("R-G-CODE", S1, "CHGET returns the code at GETPNT in A, whatever it is (00, 01, 20, 7F, FF, 'A'..'D'), in "
         "SCREEN 0 and 2.", chget, lambda c: c.a == c.codes[0]),
    Rule("R-G-PTR", S1, "GETPNT advances by one, from the buffer's 40th byte back to KEYBUF ($FBF0); PUTPNT is "
         "unchanged.", chget,
         lambda c: c.getpnt == KEYBUF + (c.off + 1) % 40 and c.putpnt == KEYBUF + (c.off + c.n) % 40),
    Rule("R-G-EI", S1, "CHGET returns with interrupts ENABLED, also when it was entered with them disabled.", chget,
         lambda c: c.iff == 1),
    Rule("R-G-FLAGS", S1, "Its flags on return are not published; the reference's here: 9A, 8A (GETPNT ending at $FB), "
         "and 4A -- Z set -- when GETPNT wrapped back to KEYBUF (R-G-F2: not the number of codes waiting).", chget,
         lambda c: c.f == CHGET_F[(c.off, c.n)]),
    Rule("R-G-QUIET", S1, "A code waiting, CHGET changes nothing else: no cursor drawn (CSRSW 0 or 1), VRAM, CSRX / "
         "CSRY, CSRSW, CNSDFG and the buffer's bytes as found.", chget, quiet),
    Rule("R-G-WAIT", S1, "With the buffer EMPTY, CHGET waits for a key and returns its code ('Q', 'R' typed), "
         "consuming it (GETPNT = PUTPNT after), with interrupts ENABLED -- also when entered with them disabled: it "
         "does not hang. VRAM cells 166 / 167 hold their garbage $5A after the call -- NOT the cursor's cell: the probe "
         "left the boot width (37, margin 2), so the cursor at column 7 is cell 168; what the wait shows is open.",
         wait, lambda c: (c.stage == 4 and c.a == c.key and c.getlo == c.putlo and c.iff == 1 and c.csrsw_out == 1
                          and (c.cur, c.cur2) == (GB, GB))),
    Rule("R-G-WFLAGS", S1, "Its flags on return after the wait: 9A, as R-G-FLAGS'.", wait, lambda c: c.f == 0x9A),
    Rule("R-S-COUNT", S2, "CHSNS returns A = PUTPNT's low byte − GETPNT's low byte (8 bits: 00 empty, 01 for one code, "
         "DB for three codes wrapped round the buffer's end) with the flags of that subtraction: Z set exactly when "
         "the buffer is empty.", lambda c: c.name == "CHSNS",
         lambda c: c.a == ((c.putpnt - c.getpnt) & 0xFF) and c.f == sub_flags(c.putpnt & 0xFF, c.getpnt & 0xFF)),
    Rule("R-S-PTR", S2, "CHSNS moves neither pointer.", lambda c: c.name == "CHSNS",
         lambda c: c.getpnt == KEYBUF + c.off and c.putpnt == KEYBUF + (c.off + c.n) % 40),
    Rule("R-S-EI", S2, "CHSNS too returns with interrupts enabled, also when entered with them disabled.",
         lambda c: c.name == "CHSNS", lambda c: c.iff == 1),
    Rule("R-S-QUIET", S2, "And changes nothing else (as R-G-QUIET), in SCREEN 0 and 2.", lambda c: c.name == "CHSNS", quiet),
]


# ---- round 2: XCHG2 (probes/bios/spec/xchg2_cases.py; scratchpad/XCHG2_run1.out), after the first review
import xchg2_cases as X2  # noqa: E402

OUTPUTS["XG2"] = ["a", "f_out", "bc", "de", "hl", "ix", "iy", "iff", "getlo", "putlo", "csrx", "csry", "csrsw",
                  "cnsdfg", "linlen", "keybuf", "before", "after", "vsum", "nchg", "chg"]
# CHGET's F on return, the reference's, by GETPNT's low byte after the call (neither "codes waiting" nor a compare of
# that byte with $18 fits all of them: the review's two readings, both refuted by this run)
CHGET_F2 = {0xF1: 0x9A, 0xF6: 0x9A, 0xFB: 0x8A, 0x05: 0x9B, 0x17: 0x9B, 0x08: 0x8B, 0x09: 0x8B}
# work-area cells the interrupt's key scan writes, which the probe's comparison did not skip: NEWKEY's last row ($FBEF:
# the probe's "byte before KEYBUF" -- its own mistake, it is a key-matrix cell) and INTCNT's high byte ($FCA3)
SCAN = {0xFBEF, 0xFCA3}

_cases1 = cases


def cases():                                     # noqa: F811
    out = _cases1()
    t = open(os.path.join(ROOT, "scratchpad", "XCHG2_run1.out")).read()
    for who, key in (("ref", "ref"), ("zb", "ours")):
        for c in X2.decode(bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))):
            c.src, c.id = "XG2", f"XG2 {c.idx:02}"
            out[who].append(c)
    return out


def g2(c):
    return c.src == "XG2"


def g2_buf(c):
    buf = [KB_GB] * 40
    for k in range(c.n):
        buf[(c.off + k) % 40] = c.codes[k]
    return buf


def g2_quiet(c):
    """Registers kept, nothing on the screen, the buffer's bytes, LINLEN, CSRSW, the cursor and CNSDFG as found, and of
    the work area only the key scan's cells changed."""
    return ((c.bc, c.de, c.hl, c.ix, c.iy) == (0x1357, 0x9BDF, 0x2468, 0x4321, 0x8765) and c.vsum == (GB * 16384) & 0xFFFF
            and c.keybuf == g2_buf(c) and c.after == 0xA5 and c.before in (0xA5, 0xFF)
            and (c.csrx, c.csry, c.csrsw, c.linlen) == (c.x, c.y, 1, 40) and c.cnsdfg == (255 if c.cns else 0)
            and set(c.chg) <= SCAN and c.nchg == len(c.chg))


for _r in RULES:
    _r.select = (lambda s: (lambda c: not g2(c) and s(c)))(_r.select)

S3 = "3. Round 2: the inputs separated (XCHG2)"

RULES += [
    Rule("R-G-CODE2", S3, "With every register garbage and A $A7 on entry (unlike the VRAM garbage), CHGET returns the "
         "code at GETPNT in A, GETPNT advanced by one (wrapping), PUTPNT unchanged, and interrupts ENABLED -- whatever "
         "the flags on entry ($00 / $FF) and whether interrupts were on.", lambda c: g2(c) and c.name == "CHGET",
         lambda c: (c.a == c.codes[0] and c.getlo == (KEYBUF + (c.off + 1) % 40) & 0xFF
                    and c.putlo == (KEYBUF + (c.off + c.n) % 40) & 0xFF and c.iff == 1)),
    Rule("R-G-F2", S3, "CHGET's F (not published) depends on where GETPNT ends: 9A at $F1 / $F6, 8A at $FB, 9B at $05 / "
         "$17, 8B at $08 / $09 (and 4A after wrapping to $F0, R-G-FLAGS). It is NOT 'the number of codes waiting' (one "
         "code at offset 10 gives 8A) nor a compare of GETPNT's low byte with $18 (that gives A2 there): the reference's "
         "values, not modelled.", lambda c: g2(c) and c.name == "CHGET", lambda c: c.f_out == CHGET_F2[c.getlo]),
    Rule("R-S-COUNT2", S3, "CHSNS: A = PUTPNT − GETPNT (low bytes) with the flags of that subtraction, whatever the "
         "flags on entry; pointers unchanged; interrupts enabled.", lambda c: g2(c) and c.name == "CHSNS",
         lambda c: (c.a == (c.putlo - c.getlo) & 0xFF and c.f_out == sub_flags(c.putlo, c.getlo)
                    and c.getlo == (KEYBUF + c.off) & 0xFF and c.iff == 1)),
    Rule("R-GS-QUIET2", S3, "Both keep BC, DE, HL, IX and IY; draw nothing (the whole VRAM's sum), also with the cursor "
         "at (1, 24) and the key line on; leave the buffer's bytes, LINLEN, CSRSW, the cursor and CNSDFG as found; and of "
         "the whole work area change only the key scan's cells (the interrupt ran).", g2, g2_quiet),
]
