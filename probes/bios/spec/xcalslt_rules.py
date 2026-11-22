#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/CALSLT.md's EXECUTABLE RULES (docs/spec-method.md §3a): the inter-slot call CALSLT ($001C) into the
probe's own target routine -- scratchpad/XCALSLT_run4.out (row N), XCALSLT_run4d.out (row D), XCALSLT_run4c.out (row
C); probes/bios/spec/xcalslt.asm documents the cases (its `cases:` table, read here) and the 40-byte record. CALLF's
and CALBAS's rules (xcallf_rules.py, xcalbas_rules.py) read the same runs: `load()` serves all three."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/CALSLT.md"
RUNS = [("XCALSLT_run4.out", "N"), ("XCALSLT_run4d.out", "D"), ("XCALSLT_run4c.out", "C")]


def _cases():
    src = open(os.path.join(HERE, "xcalslt.asm")).read()
    body = src[src.index("\ncases:\n"):]
    rows = re.findall(r"db\s+(\d), (\d), \$([0-9A-F]{2}), (\d), (\d), \$([0-9A-F]{2})", body)
    if len(rows) != 20:
        sys.exit(f"FAIL: xcalslt.asm's case table gave {len(rows)} rows, not 20")
    return [(int(a), int(b), int(c, 16), int(d), int(e), int(f, 16)) for a, b, c, d, e, f in rows]


CASES = _cases()   # op (0 CALSLT, 1 CALLF, 2 CALBAS, 3 control), where, entry F, ei, secondary preset, CALSLT's IY low
TGT = 0x4010
IN = dict(bc=0x1357, de=0x9BDF, hl=0x2468)
OUT = dict(af=0xC3D7, bc=0x1122, de=0x3344, hl=0x5566, ix=0xA55A, iy=0x5AA5)
FULL = ["a8in", "iffin", "secin", "sp", "afin", "bcin", "dein", "hlin", "ixin", "iyin", "af", "bc", "de", "hl", "ix",
        "iy", "a8", "iff", "sec", "ran"]
# a RAM-target case on a row whose machines' RAM slots differ in kind (the VG-8020's 3, zerobas's expanded 3-0): the
# stack depth, IY in the target and the secondary selection come from different paths (and the secondary preset runs
# on zerobas only), so they are not outputs of this comparison -- row C compares them, kind for kind
OUTPUTS = {"XC": FULL, "XCK": [f for f in FULL if f not in ("sp", "iyin", "secin", "sec")],
           # a cartridge case with a secondary preset on rows N / D: the preset runs on zerobas only (slot 3 is not
           # expanded on the VG-8020), so the secondary selection is not compared there
           "XCP": [f for f in FULL if f not in ("secin", "sec")]}


def load(op):
    out = {"ref": [], "zb": []}
    for name, row in RUNS:
        t = open(os.path.join(ROOT, "scratchpad", name)).read()
        blocks = {}
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            if b[0] != 0xA5 or len(b) < 6 + 40 * len(CASES) or b[5 + 40 * len(CASES)] != 0xC3:
                sys.exit(f"FAIL: the {name} block is not complete (no sentinel)")
            blocks[who] = b
        same_kind = (blocks["ref"][3] & 0x80) == (blocks["zb"][3] & 0x80)
        for who in ("ref", "zb"):
            b = blocks[who]
            a8b, exp3, ramid, cartid = b[1], b[2] & 0x80, b[3], b[4]
            for i, (cop, wh, ef, ei, ps, iylo) in enumerate(CASES):
                if cop != op and not (op == 0 and cop == 3):
                    continue
                r = b[5 + 40 * i:45 + 40 * i]
                w = lambda k: r[k] | r[k + 1] << 8  # noqa: E731
                ram = wh >= 2
                sid = ramid if ram else cartid
                page = 2 if wh in (1, 3) else 1
                if cop >= 2:
                    a8pre = a8b if cop == 3 else a8b | 0x0C
                elif wh == 2:
                    a8pre = a8b
                elif wh == 3:
                    a8pre = (a8b & 0xCF) | (cartid & 3) << 4
                else:
                    a8pre = a8b | 0x0C
                secpre = ({1: 0x04, 2: 0x10}.get(ps, 0) if exp3 else 0)   # boot: 3-0 (0); the preset sets 3-1
                src = "XC" if same_kind else ("XCK" if ram else ("XCP" if ps else "XC"))
                out[who].append(NS(src=src, id=f"XC {row}{i:02}", row=row,
                                   op=cop, wh=wh, ef=ef, ei=ei, ps=ps, iylo=iylo, sid=sid, page=page, a8b=a8b,
                                   a8pre=a8pre, secpre=secpre, exp=bool(sid & 0x80),
                                   addr=TGT + (0x4000 if page == 2 else 0),
                                   a8in=r[0], iffin=r[1], secin=r[2], sp=w(3), afin=w(5), bcin=w(7), dein=w(9),
                                   hlin=w(11), ixin=w(13), iyin=w(15), af=w(17), bc=w(19), de=w(21), hl=w(23),
                                   ix=w(25), iy=w(27), a8=r[29], iff=r[30], sec=r[31], ran=r[32]))
    return out


def cases():
    return load(0)


def switched(c):
    p = c.page
    return (c.a8pre & ~(3 << 2 * p) & 0xFF) | ((c.sid & 3) << 2 * p)


def unread(op):
    return {f"XC {row}{i:02}": (["secin", "sec"], "rows N / D: slot 3 is not expanded on the VG-8020, so the probe "
                                "records 0 itself there (R-*-SEC reads the selection on the cf3300 row)")
            for row in "ND" for i, cs in enumerate(CASES)
            if (cs[0] == op or (op == 0 and cs[0] == 3)) and cs[1] < 2 and not cs[4]}


def core(tag, S1, sel):
    """the rules CALSLT and CALLF share (sel picks the op's cases)"""
    return [
        Rule(f"R-{tag}-RUN", S1, "The target runs in the slot named, its page switched to it: the slot register inside "
             "it has that page's two bits replaced by the slot's primary number -- page 1 or 2, the cartridge or the "
             "RAM slot, from a page set to another slot by hand.", sel,
             lambda c: c.ran == 1 and c.a8in == switched(c)),
        Rule(f"R-{tag}-IN", S1, "AF, BC, DE and HL reach the target as the caller set them (A $A5, F $00 / $5A / $FF), "
             "and IX holds the target's address.", sel,
             lambda c: (c.afin == 0xA500 | c.ef and (c.bcin, c.dein, c.hlin) == (IN["bc"], IN["de"], IN["hl"])
                        and c.ixin == c.addr)),
        Rule(f"R-{tag}-OUT", S1, "AF, BC, DE, HL, IX and IY come back as the target left them ($C3D7, $1122, $3344, "
             "$5566, $A55A, $5AA5 -- the target changes IX and IY too).", sel,
             lambda c: (c.af, c.bc, c.de, c.hl, c.ix, c.iy) == tuple(OUT[k] for k in ("af", "bc", "de", "hl", "ix",
                                                                                     "iy"))),
        Rule(f"R-{tag}-SLOT", S1, "The slot register after the call is as before it (the page set by hand put back).",
             sel, lambda c: c.a8 == c.a8pre),
        Rule(f"R-{tag}-DI", S1, "Interrupts are off in the target and after the call, whether they were on or off on "
             "entry (the probe's control record, on CALSLT's page, shows the readout reading them on).", sel,
             lambda c: c.iffin == 0 and c.iff == 0),
        Rule(f"R-{tag}-SEC", S1, "For the expanded RAM slot 3-0 (the cf3300 row), the target's page selects 3-0 in "
             "slot 3's secondary register during the call -- from a selection of 3-1 set by hand before it, in page 1 "
             "and page 2 -- and the selection is as before the call after it; a target in a slot that is not "
             "expanded (the cartridge) leaves a 3-1 selection alone, during the call and after.",
             lambda c: sel(c) and c.row == "C",
             lambda c: (c.secin == ((c.secpre & ~(3 << 2 * c.page) & 0xFF) if c.exp else c.secpre)
                        and c.sec == c.secpre)),
    ]


S1 = "1. CALSLT ($001C): call the address in IX in the slot in IY's high byte"
CS = lambda c: c.op == 0  # noqa: E731

RULES = core("CS", S1, CS) + [
    Rule("R-CS-IY", S1, "In the target IY is as the caller set it (the slot ID over the caller's low byte, $65 or "
         "$C3) for a slot that is not expanded; for the expanded RAM slot 3-0 (the cf3300 row) it is $0314, whatever "
         "the caller's low byte ($65, $C3, $3C) and the page.", lambda c: CS(c) and c.src in ("XC", "XCP"),
         lambda c: c.iyin == ((0x0314) if c.exp else (c.sid << 8 | c.iylo))),
    Rule("R-CS-SP", S1, "The target runs 6 bytes below the caller's SP (CALL's return address included) for a slot "
         "that is not expanded, 14 for the expanded RAM slot 3-0 (the cf3300 row).",
         lambda c: CS(c) and c.src in ("XC", "XCP"), lambda c: c.sp == (14 if c.exp else 6)),
    Rule("R-CS-CTL", S1, "The probe's own CONTROL record calls the target directly, interrupts on: the readout reads "
         "them on in the target and after, the slot register unswitched, 2 bytes of stack (the CALL), the registers "
         "as passed and as the target left them.", lambda c: c.op == 3,
         lambda c: (c.iffin == 1 and c.iff == 1 and c.ran == 1 and c.a8in == c.a8 == c.a8b and c.sp == 2
                    and c.afin == 0xA500 | c.ef and (c.ixin, c.iyin) == (0x4321, 0x8765)
                    and (c.bcin, c.dein, c.hlin) == (IN["bc"], IN["de"], IN["hl"]) and c.secin == c.sec == 0
                    and (c.af, c.bc, c.de, c.hl, c.ix, c.iy) == tuple(OUT[k] for k in ("af", "bc", "de", "hl", "ix",
                                                                                      "iy")))),
]

UNREAD = unread(0)
