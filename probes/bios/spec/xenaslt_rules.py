#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/ENASLT.md's EXECUTABLE RULES (docs/spec-method.md §3a): ENASLT ($0024) switching pages 1 and 2 to the
RAM slot and the probe's own cartridge -- scratchpad/XENASLT_run4.out (row N), XENASLT_run4d.out (row D),
XENASLT_run4c.out (row C); probes/bios/spec/xenaslt.asm documents the header, the cases and the 16-byte record. Round 2,
the secondary slot on the cf3300 row: scratchpad/XENASLT2_run5c.out (probes/bios/spec/xenaslt2.asm, reading 3-1 only
at its "AB" header, Joost's ruling of 2026-11-18)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/ENASLT.md"
RUNS = [("XENASLT_run4.out", "N"), ("XENASLT_run4d.out", "D"), ("XENASLT_run4c.out", "C")]
OUTPUTS = {"XE": ["a", "f", "iff", "a8", "sec", "slt", "moved", "wit", "b", "c", "d", "e"],
           "XE2": ["a", "f", "a8", "sec", "slt3", "wit", "b", "c", "d", "e", "iff"]}
CASES2 = [(0x83, 0x04, 0x04), (0x87, None, None), (0x87, 0x08, 0x08), (0x87, 0x04, 0x04), (0x83, 0x25, 0x25),
          (0x87, 0x29, 0x29), (0x83, 0x25, 0x1A), (0x87, 0x19, 0x26), (0x87, None, None)]
# CASES2 (xenaslt2.asm): ID, the presets of slot 3's secondary register and of SLTTBL+3 (pages 0-2; None: boot);
# case 8 enters with interrupts on
CASES = [(0, 0x40, 0x00, 0, 0), (1, 0x5A, 0xFF, 0, 0), (0, 0x7F, 0xFF, 1, 0), (1, 0xA5, 0x00, 0, 0),
         (0, 0x80, 0x00, 1, 0), (1, 0x40, 0x00, 1, 0), (0, 0xBF, 0xFF, 0, 0), (0, 0x80, 0xFF, 0, 1),
         (0, 0x9C, 0x00, 1, 1)]   # which (0 RAM, 1 cartridge), H, entry F, ei, preset (1: page 2 := the cartridge)
RAMMARK = {1: (0x5A, 0xA5), 2: (0xC6, 0x6C)}       # what the probe wrote into the RAM slot at $4000 / $8002
CARTSHOW = {1: (0x41, 0x42), 2: (0x10, 0x40)}      # the cartridge: "AB"; page 2 its 16 KB image mirrored (init $4010)


def cases():
    out = {"ref": [], "zb": []}
    for name, row in RUNS:
        t = open(os.path.join(ROOT, "scratchpad", name)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            n = len(CASES)
            if b[0] != 0xA5 or len(b) < 14 + 16 * n or b[13 + 16 * n] != 0xC3:
                sys.exit(f"FAIL: the {name} block is not complete (no sentinel)")
            a8b, exptbl, sltb, secb, ramid, cartid = b[1], bytes(b[2:6]), bytes(b[6:10]), b[10], b[11], b[12]
            # SLTTBL before each call: the probe's junk ($1B + $11 * k) for every slot that is not expanded
            sltpre = bytes(sltb[k] if exptbl[k] & 0x80 else 0x1B + 0x11 * k for k in range(4))
            for i, (wh, h, ef, ei, pr) in enumerate(CASES):
                r = b[13 + 16 * i:29 + 16 * i]
                sid = cartid if wh else ramid
                out[who].append(NS(src="XE", id=f"XE {row}{i}", row=row, cart=wh, h=h, page=h >> 6, ef=ef, ei=ei,
                                   sid=sid, a8b=a8b, sltb=sltpre, secb=secb, pr=pr, a=r[0], f=r[1], iff=r[2], a8=r[3], sec=r[4],
                                   slt=bytes(r[5:9]), moved=r[9], wit=(r[10], r[11]), b=r[12], c=r[13], d=r[14],
                                   e=r[15]))
    t = open(os.path.join(ROOT, "scratchpad", "XENASLT2_run5c.out")).read()
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        n = len(CASES2)
        if b[0] != 0xA5 or len(b) < 5 + 12 * n or b[4 + 12 * n] != 0xC3:
            sys.exit("FAIL: the XENASLT2_run5c.out block is not complete (no sentinel)")
        a8b, secb, slt3b = b[1], b[2], b[3]
        for i, (sid, ps, pt) in enumerate(CASES2):
            r = b[4 + 12 * i:16 + 12 * i]
            out[who].append(NS(src="XE2", id=f"XE2 {i}", row="C2", sid=sid, ps=ps, pt=pt, page=1, ei=int(i == 8), a8b=a8b, secb=secb,
                               slt3b=slt3b, a=r[0], f=r[1], a8=r[2], sec=r[3], slt3=r[4], wit=(r[5], r[6]), b=r[7],
                               c=r[8], d=r[9], e=r[10], iff=r[11]))
    return out


R1 = lambda c: c.src == "XE"  # noqa: E731


def pre(c, boot):
    """slot 3's secondary selection (or SLTTBL+3) before the call: the boot one, or the case's preset (pages 0-2)."""
    return boot if c.ps is None else (boot & 0xC0) | (c.ps & 0x3F)


def NEWSEC(c):
    """the new selection: the REGISTER's (not SLTTBL+3's) other fields, the page's field the ID's secondary."""
    return (pre(c, c.secb) & 0xF3) | ((c.sid >> 2 & 3) << 2)
R2 = lambda c: c.src == "XE2"  # noqa: E731


def logical(a):
    return (a & 0x80) | (0x40 if a == 0 else 0) | (a & 0x28) | (0x04 if bin(a).count("1") % 2 == 0 else 0)


def new_a8(c):
    p = c.page
    return (c.a8b & ~(3 << 2 * p) & 0xFF) | ((c.sid & 3) << 2 * p)


S1 = "1. ENASLT ($0024): switch the page holding H to the slot A names, and leave it switched"

RULES = [
    Rule("R-EN-MAP", S1, "After the call the page holding H shows the slot A names, read without switching anything: "
         "the RAM slot's markers, the cartridge's \"AB\" in page 1 and its image mirrored in page 2 -- from a page "
         "that held another slot (page 1: the cartridge to RAM; page 2: RAM to the cartridge, and the cartridge -- set by "
         "hand -- to RAM) or the same one.",
         R1, lambda c: c.wit == (CARTSHOW if c.cart else RAMMARK)[c.page]),
    Rule("R-EN-A8", S1, "The slot register's two bits for that page are replaced by the slot's primary number; the "
         "other pages keep theirs. Only bits 6-7 of H count (H $40, $5A, $7F; $80, $9C, $A5, $BF).", R1,
         lambda c: c.a8 == new_a8(c)),
    Rule("R-EN-AF", S1, "A is the new slot register and F a logical result's on it (S, Z, bits 5 / 3 from it, P/V "
         "its parity; H, N, C clear), whatever F was on entry ($00 / $FF).", R1,
         lambda c: c.a == new_a8(c) and c.f == logical(new_a8(c))),
    Rule("R-EN-DI", S1, "Interrupts are off on return, whether they were on or off on entry.", R1,
         lambda c: c.iff == 0),
    Rule("R-EN-REGS", S1, "B is the slot's primary number in the page's two bits, C the complement of the page's "
         "mask, D the primary number in all four pages' bits ($FF for slot 3, $55 for slot 1, $AA for slot 2) and E "
         "the page's mask; HL, IX and IY are kept.", R1,
         lambda c: (c.b == (c.sid & 3) << 2 * c.page and c.c == (~(3 << 2 * c.page)) & 0xFF
                    and c.d == (c.sid & 3) * 0x55 and c.e == 3 << 2 * c.page and c.moved & 0x70 == 0)),
    Rule("R-EN-SLT", S1, "SLTTBL and slot 3's secondary selection are as before the call, for these targets: the "
         "SLTTBL entries of the slots that are not expanded hold junk the probe put there ($1B + $11 per slot) and keep "
         "it; and on the cf3300 row slot 3's secondary selection stays 3-0 for 3-0 named where 3-0 is selected.", R1,
         lambda c: c.slt == c.sltb and (c.row != "C" or c.sec == c.secb)),
    Rule("R-EN-SUB", S1, "For the expanded slot 3 (the cf3300 row), ENASLT puts the ID's secondary number into the "
         "page's field of slot 3's secondary register, whatever selection the page had (3-0, 3-1 or 3-2, set by hand); "
         "the other pages' fields keep the register's (3-1 / 3-2 in pages 0 and 2). SLTTBL+3 is then that same new "
         "byte: where SLTTBL+3 was preset to another pattern than the register ($1A against $25, $26 against $19), "
         "it takes the register's value, not its own other fields: naming 3-1 ($87) for page 1 shows 3-1's header \"AB\", "
         "naming 3-0 ($83) the RAM's markers, read directly after the call.", R2,
         lambda c: (c.sec == NEWSEC(c) and c.slt3 == NEWSEC(c)
                    and c.wit == ((0x41, 0x42) if c.sid == 0x87 else (0x5A, 0xA5)))),
    Rule("R-EN-SUB2", S1, "And as R-EN-A8 / R-EN-AF / R-EN-DI / R-EN-REGS there: the slot register's page-1 field "
         "becomes 3 ($FC), A that value, F its logical flags ($AC), interrupts off, B $0C, C $F3, D $FF, E $0C.", R2,
         lambda c: (c.a8 == c.a == (c.a8b & 0xF3) | 0x0C and c.f == logical(c.a8) and c.iff == 0
                    and (c.b, c.c, c.d, c.e) == (0x0C, 0xF3, 0xFF, 0x0C))),
]


UNREAD = {f"XE {row}{i}": (["sec"], "rows N / D: slot 3 is not expanded on the VG-8020, so the probe records 0 itself "
                           "there; R-EN-SLT reads it on the cf3300 row")
          for row in "ND" for i in range(len(CASES))}
