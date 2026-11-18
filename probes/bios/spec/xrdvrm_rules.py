#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/RDVRM.md's EXECUTABLE RULES (docs/spec-method.md §3a): RDVRM ($004A) -- the run the VRAM access calls share
(probes/bios/spec/xvram.asm, op 0; the loader and the model are xvram_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xvram_model as V  # noqa: E402

PAGE = "docs/bios/RDVRM.md"
OUTPUTS = V.OUTPUTS


def cases():
    return V.load(0)


S1 = "1. RDVRM ($004A): read a VRAM byte"
ALL = lambda c: True  # noqa: E731

RULES = [
    Rule("R-RV-A", S1, "A := the VRAM byte at HL AND $3FFF (HL $1234, $3FFF, $0000, $0812, $2034, and $4123 / $C123 / "
         "$FFFF, which read $0123 / $0123 / $3FFF).", ALL, lambda c: c.a == V.model(c)[0][c.chl & 0x3FFF]),
    Rule("R-RV-F", S1, "F is the flags of (H AND $3F) as an AND leaves them: S, Z, bits 5 / 3 from that value, H set, "
         "P/V the even parity, N and C clear -- whatever A and F were on entry (A $A7, $00, $5A; F $00, $FF, $A5, $5A).", ALL,
         lambda c: c.f == V.logical((c.chl >> 8) & 0x3F) | 0x10),
    Rule("R-RV-KEEP", S1, "BC, DE, HL, IX and IY are kept.", ALL, lambda c: V.keep(c, ["bc", "de", "hl", "ix", "iy"])),
    V.mem_rule("RV", S1, "VRAM is not changed: the probe's VRAM windows read back as it set them."),
    V.port_rule("RV", S1, "The VDP is left reading the byte after HL: the next read of port $98 returns the VRAM byte at "
                "(HL + 1) AND $3FFF."),
    V.ei_rule("RV", S1),
]

UNREAD = V.unread(0)
