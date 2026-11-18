#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/DISSCR.md's EXECUTABLE RULES (docs/spec-method.md §3a): DISSCR ($0041) -- the run docs/bios/WRTVDP.md
reads (probes/bios/spec/xvdpreg.asm, op 1; the loader is xwrtvdp_rules.load). ENASCR's module reuses `screen()`."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xwrtvdp_rules as W  # noqa: E402

PAGE = "docs/bios/DISSCR.md"
OUTPUTS = W.OUTPUTS


def cases():
    return W.load(1)


def screen(tag, section, new, what):
    """the rules DISSCR and ENASCR share: R#1 := new(RG1SAV), RG1SAV := the same, as WRTVDP with C = 1"""
    ALL = lambda c: True  # noqa: E731
    return [
        Rule(f"R-{tag}-R1", section, f"VDP register R#1 := RG1SAV ($F3E0) {what}, as the VDP holds it (bit 2 reads 0); "
             "the other registers keep their values. RG1SAV is the source, not R#1: the probe sets R#1 to $C0 by hand "
             "and RG1SAV to $00, $FF, $A0, $E2, $5A, $A5, $40 or $BF.", ALL,
             lambda c: c.vdp == W.after_write(c, 1, new(c.rg1))[2]),
        Rule(f"R-{tag}-SAV", section, f"RG1SAV := that same value; every other byte of $F3DF-$F3EE keeps its value.", ALL,
             lambda c: (c.sav, c.e7) == W.after_write(c, 1, new(c.rg1))[:2]),
        Rule(f"R-{tag}-REGS", section, "On return A is the new value, B = 0, C = 1 and F = $A4, as "
             "[WRTVDP](WRTVDP.md) leaves them for C = 1 (F whatever it was on entry); interrupts are on, whether "
             "they were on or off before; DE, HL, IX and IY are kept.", ALL,
             lambda c: (c.a == new(c.rg1) and c.b == 0 and c.c == 1 and c.f == 0xA4 and c.iff == 1
                        and c.moved == 0)),
    ]


S1 = "1. DISSCR ($0041): blank the screen"
RULES = screen("DS", S1, lambda v: v & 0xBF, "with bit 6 (the screen-enable bit) cleared")
