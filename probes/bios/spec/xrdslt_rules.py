#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/RDSLT.md's EXECUTABLE RULES (docs/spec-method.md §3a): RDSLT ($000C) on the machine's RAM slot and the
probe's own cartridge slot -- scratchpad/XRDSLT_run5.out (the diskless row: $A8 = $F4 at boot),
scratchpad/XRDSLT_run5d.out (the disk row: the VG-8020 with a disk interface, $A8 = $F8) and
scratchpad/XRDSLT_run5c.out (the cf3300 row: the CF-3300, whose RAM is the expanded slot 3-0 as zerobas's is);
probes/bios/spec/xrdslt.asm documents the header, the cases and the 12-byte record. docs/bios/WRSLT.md's rules (xwrslt_rules.py) read the same
runs: `load()` serves both."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/RDSLT.md"


def BC(c):
    p = c.addr >> 14
    return c.b == (c.sid & 3) << 2 * p and c.c == (~(3 << 2 * p)) & 0xFF


def BCX(c):
    return c.b == c.a8pre and c.c == 0xC0


PLAINBC = lambda c: c.op != 2 and c.src == "XR" and not c.sid & 0x80  # noqa: E731
EXPBC = lambda c: c.op != 2 and c.src == "XR" and c.sid & 0x80  # noqa: E731
CALL = lambda c: c.op != 2  # noqa: E731


def SEC(c):
    """slot 3's secondary selection expected after the call: the boot one, with the case's preset."""
    return {0: c.secboot, 1: (c.secboot & 0xFC) | 0x01, 2: (c.secboot & 0xF3) | 0x04}[c.ps]


EXPROW = lambda c: c.op != 2 and c.row == "C"  # noqa: E731
OUTPUTS = {"XR": ["a", "f", "iff", "a8", "sec", "moved", "wit", "b", "c", "d", "e", "pre"],
           # a RAM case on a row whose two machines' RAM slots differ in kind (the VG-8020's slot 3, zerobas's
           # expanded 3-0): B and C come from different paths there, so they are not outputs of this comparison --
           # the cf3300 row compares zerobas's kind with a reference of the same kind
           # (and slot 3's secondary selection: expanded on zerobas, not on the VG-8020)
           "XRK": ["a", "f", "iff", "a8", "moved", "wit", "d", "e", "pre"]}
RUNS = [("XRDSLT_run5.out", "N"), ("XRDSLT_run5d.out", "D"), ("XRDSLT_run5c.out", "C")]
# the probe's cases, read from its own table (`cases:` in probes/bios/spec/xrdslt.asm): op (0 WRSLT, 1 RDSLT), which (0
# RAM, 1 cartridge), address, value (E), entry F, ei, extra ID bits, the secondary preset (0 none, 1 page 0 := 3-1,
# 2 page 1 := 3-1; applied only where slot 3 is expanded), the slot-register preset (1: page 1 := slot 0). Op 2 is the
# CONTROL record (interrupts on, no call); RDSLT's page carries it.
def _cases():
    src = open(os.path.join(HERE, "xrdslt.asm")).read()
    body = src[src.index("\ncases:\n"):]
    rows = re.findall(r"db\s+(\d+), (\d+)\s*\n\s+dw\s+\$([0-9A-F]{4})\s*\n\s+db\s+\$([0-9A-F]{2}), \$([0-9A-F]{2}), "
                      r"(\d), \$([0-9A-F]{2}), (\d), (\d)", body)
    if len(rows) != 37:
        sys.exit(f"FAIL: xrdslt.asm's case table gave {len(rows)} rows, not 37")
    return [(int(a), int(b), int(c, 16), int(d, 16), int(e, 16), int(f), int(g, 16), int(h), int(k))
            for a, b, c, d, e, f, g, h, k in rows]


CASES = _cases()
# the bytes RDSLT reads from the cartridge: the probe's own image ("AB", then init's low byte)
CART = {0x4000: 0x41, 0x4001: 0x42, 0x4002: 0x10, 0x8002: 0x10}   # $8002: the 16 KB image mirrored in page 2


def load(op):
    out = {"ref": [], "zb": []}
    for name, row in RUNS:
        t = open(os.path.join(ROOT, "scratchpad", name)).read()
        blocks = {}
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            n = len(CASES)
            if b[0] != 0xA5 or len(b) < 18 + 12 * n or b[17 + 12 * n] != 0xC3:
                sys.exit(f"FAIL: the {name} block is not complete (no sentinel)")
            blocks[who] = b
        same_kind = (blocks["ref"][11] & 0x80) == (blocks["zb"][11] & 0x80)   # the RAM slot IDs' bit 7
        for who in ("ref", "zb"):
            b = blocks[who]
            a8boot, secboot, ramid, cartid = b[1], b[10], b[11], b[12]
            for i, (cop, wh, ad, va, ef, ei, xb, ps, a8p) in enumerate(CASES):
                if cop != op and not (op == 1 and cop == 2):
                    continue
                r = b[17 + 12 * i:29 + 12 * i]
                sid = (cartid if wh else ramid) | xb
                out[who].append(NS(src="XR" if wh or same_kind else "XRK", id=f"XR {row}{i:02}", row=row, op=cop,
                                   cart=wh, addr=ad, val=va, ef=ef, ei=ei, xb=xb, ps=ps, sid=sid, a8boot=a8boot, idx=i,
                                   a8pre=(a8boot & 0xF3) if a8p else a8boot, a8p=a8p,
                                   secboot=secboot, a=r[0], f=r[1], iff=r[2], a8=r[3], sec=r[4], moved=r[5], wit=r[6],
                                   b=r[7], c=r[8], d=r[9], e=r[10], pre=r[11]))
    return out


def cases():
    return load(1)


def logical(a):
    return (a & 0x80) | (0x40 if a == 0 else 0) | (a & 0x28) | (0x04 if bin(a).count("1") % 2 == 0 else 0)


def page(c):
    return c.addr >> 14


def switched(c):
    """The slot register with the case's page set to the slot's primary."""
    p = page(c)
    return (c.a8pre & ~(3 << 2 * p) & 0xFF) | ((c.sid & 3) << 2 * p)


S1 = "1. RDSLT ($000C): read a byte from an address in a slot"

RULES = [
    Rule("R-RD-A", S1, "A is the byte at HL in the slot A names -- the byte a read by switching the slot register by "
         "hand finds before and after the call: RAM a WRSLT wrote just before, in pages 0 and 1 a slot other than the "
         "one mapped there ($0000 to $7FFF), in pages 2 and 3 the slot already mapped ($8ABC to $EE40); and the "
         "cartridge's own bytes in pages 1 and 2, whatever slot those pages hold before the call.",
         CALL, lambda c: c.a == c.wit == c.pre and (not c.cart or c.a == CART[c.addr])),
    Rule("R-RD-IGN", S1, "Bits 4-6 of the slot ID are ignored (a RAM ID with $70 added reads the same RAM).",
         lambda c: CALL(c) and c.xb != 0, lambda c: c.a == c.wit == c.pre),
    Rule("R-RD-SLOT", S1, "The slot register ($A8) is as before the call -- its boot value, or with page 1 set to slot "
         "0 by hand ($F0): a second value on every machine.",
         CALL, lambda c: c.a8 == c.a8pre),
    Rule("R-RD-SEC", S1, "Where slot 3 is expanded (the cf3300 row), a read naming 3-0 reaches 3-0's RAM from a page "
         "whose secondary selection is 3-1 (set by hand before the call), and leaves that selection 3-1 after it; the "
         "other pages keep 3-0. Only 3-0 holds RAM: whether 3-1 there differs from 3-0 is not read (clean room).", EXPROW, lambda c: c.sec == SEC(c)),
    Rule("R-RD-DI", S1, "Interrupts are off on return, whether they were on or off on entry.", CALL,
         lambda c: c.iff == 0),
    Rule("R-RD-E", S1, "E is the byte read (A); D the slot register as restored. HL, IX and IY are kept.",
         CALL, lambda c: c.e == c.a and c.d == c.a8pre and c.moved & 0x70 == 0),
    Rule("R-RD-F", S1, "F is a logical result's on the slot register with the read page switched to the slot (S, Z, "
         "bits 5 / 3 from it, P/V its parity; H, N, C clear) -- whatever F was on entry ($00 / $FF). Page 1 shows it: "
         "$F4 with page 1 set to slot 3 is $FC, F $AC, where the restored $F4 would give $A0.",
         CALL, lambda c: c.f == logical(switched(c))),
    Rule("R-RD-BC", S1, "For a slot that is not expanded (the cartridge, slot 1 or 2, in pages 1 and 2), B is the "
         "slot's number in the page's two bits and C the complement of the page's mask (slot 1: page 1 B $04, C $F3; "
         "page 2 B $10, C $CF).", PLAINBC, BC),
    Rule("R-RD-FIELD", S1, "The page's two bits of the slot register are REPLACED by the slot, not ORed with it: the "
         "cartridge's ID at $8002, where page 2 is RAM holding $C6, reads the cartridge's byte ($10, its image "
         "mirrored there): an OR would read slot 3. (An AND is excluded by the page-0 RAM cases of R-RD-A: slot 3 "
         "named where slot 0 is mapped.)", lambda c: c.cart and c.addr == 0x8002, lambda c: c.a == 0x10 == c.wit),
    Rule("R-RD-SEC2", S1, "Those reads return 3-0's byte, not a fixed 3-1 byte: two reads at each address under the "
         "same preset return the two values written there before ($0456: $2D, then $B4; $5678: $D2, then $4B).",
         lambda c: EXPROW(c) and c.ps, lambda c: c.a == CASES[c.idx - 1][3]),
    Rule("R-RD-CTL", S1, "The probe's own CONTROL record (interrupts on, no call) reads interrupts ON, and its A / F, "
         "registers, slot register and witness as set: the IFF readout can report 1.", lambda c: c.op == 2,
         lambda c: c.iff == 1 and c.a == c.sid and c.f == c.ef and c.moved == 0 and c.a8 == c.a8boot and c.d == 0x9B
         and c.e == c.val and c.wit == c.pre and (c.b, c.c) == (0x13, 0x57) and c.sec == c.secboot),
    Rule("R-RD-BCX", S1, "For the expanded RAM slot 3-0 (the cf3300 row), B is the slot register's value as it was "
         "before the call ($F4, or $F0 with page 1 set to slot 0 -- not the switched value: page 0 gives $F0, not "
         "$F3) and C $C0, in every page.", EXPBC, BCX),
]


# B / C in the RAM cases: the reference's RAM is slot 3, not expanded; zerobas's is slot 3-0, expanded -- the two take
# different paths because the MACHINES differ, not their BIOSes, and B / C are not published (RDSLT destroys BC).
def unread(op):
    return {f"XR {row}{i:02}": (["sec"], "slot 3's secondary selection on a VG-8020 row's cartridge case: the reference's "
                                "slot 3 is not expanded and the probe records 0 itself (R-*-SEC reads it on the cf3300 "
                                "row)")
            for row in "ND" for i, cs in enumerate(CASES) if cs[0] == op and cs[1] == 1}


UNREAD = unread(1)
