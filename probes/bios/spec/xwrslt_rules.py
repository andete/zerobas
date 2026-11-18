#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/WRSLT.md's EXECUTABLE RULES (docs/spec-method.md §3a): WRSLT ($0014) on the machine's RAM slot --
scratchpad/XRDSLT_run5.out, scratchpad/XRDSLT_run5d.out and scratchpad/XRDSLT_run5c.out, the WRSLT cases of the probe docs/bios/RDSLT.md reads
(probes/bios/spec/xrdslt.asm; the loader is xrdslt_rules.load)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xrdslt_rules as R  # noqa: E402

PAGE = "docs/bios/WRSLT.md"
OUTPUTS = R.OUTPUTS


def cases():
    one, two = R.load(0), R.load2(0)
    return {w: one[w] + two[w] for w in one}


S1 = "1. WRSLT ($0014): write a byte to an address in a slot"

RULES = [
    Rule("R-WR-W", S1, "E lands at HL in the slot A names: a read by switching the slot register by hand finds another "
         "byte there before the call and E after -- in pages 0 and 1 a slot other than the one mapped there ($0000 to "
         "$7FFF), in pages 2 and 3 the slot already mapped ($8ABC to $EE40).", R.CALL,
         lambda c: c.wit == c.val and c.pre != c.val),
    Rule("R-WR-IGN", S1, "Bits 4-6 of the slot ID are ignored (a RAM ID with $70 added writes the same RAM).",
         lambda c: c.xb != 0, lambda c: c.wit == c.val and c.pre != c.val),
    Rule("R-WR-SLOT", S1, "The slot register ($A8) is as before the call -- its boot value, or with page 1 set to slot "
         "0 by hand ($F0): a second value on every machine.",
         R.CALL, lambda c: c.a8 == c.a8pre),
    Rule("R-WR-SEC", S1, "Where slot 3 is expanded (the cf3300 row), a write naming 3-0 reaches 3-0's RAM from a page "
         "whose secondary selection is 3-1 (set by hand before the call), and leaves that selection 3-1 after it; the "
         "other pages keep 3-0. Only 3-0 holds RAM: whether 3-1 there differs from 3-0 is not read (clean room).", R.EXPROW, lambda c: c.sec == R.SEC(c)),
    Rule("R-WR-DI", S1, "Interrupts are off on return, whether they were on or off on entry.", R.CALL,
         lambda c: c.iff == 0),
    Rule("R-WR-A", S1, "A and D are the slot register as restored; E, HL, IX and IY are kept.", R.CALL,
         lambda c: c.a == c.a8pre and c.d == c.a8pre and c.e == c.val and c.moved & 0x78 == 0),
    Rule("R-WR-F", S1, "F is a logical result's on the slot register with the written page switched to the slot (S, "
         "Z, bits 5 / 3 from it, P/V its parity; H, N, C clear) -- whatever F was on entry ($00 / $FF). Page 1 carries "
         "it: $F4 with page 1 set to slot 3 is $FC, F $AC, where the restored $F4 would give $A0.",
         R.CALL, lambda c: c.f == R.logical(R.switched(c))),
    Rule("R-WR-SUB", S1, "Round 6 (the cf3300 row): WRSLT naming 3-0 ($83) at $4000 -- where 3-1 holds its header -- "
         "returns with the slot register and the secondary selection as before, A the slot register, F a logical "
         "result's on the switched one ($AC); RDSLT then reads the $18 back from 3-0 (RDSLT's page).", R.R6,
         lambda c: c.a == c.a8boot == c.a8 and c.sec == R.SEC2(c) and c.f == R.logical(R.switched(c))),
    Rule("R-WR-BCX", S1, "For the expanded RAM slot 3-0 (the cf3300 row), B is the slot register's value as it was "
         "before the call ($F4, or $F0 with page 1 set to slot 0 -- not the switched value: page 0 gives $F0, not "
         "$F3) and C $C0, in every page.", R.EXPBC, R.BCX),
]

UNREAD = R.unread(0)
