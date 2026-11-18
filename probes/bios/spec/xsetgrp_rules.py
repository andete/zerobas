#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/SETGRP.md's EXECUTABLE RULES (docs/spec-method.md §3a): SETGRP ($007E) -- the run the SETxxx calls share
(probes/bios/spec/xset.asm, op 2; the loader, the model and the rules are xset_rules)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xset_rules as X  # noqa: E402

PAGE = "docs/bios/SETGRP.md"
OUTPUTS = X.OUTPUTS


def cases():
    return X.load(2)


S1 = "1. SETGRP ($007E): set the VDP up for high-resolution graphics"
RULES = X.rules(2, "GR", S1, 'RG0SAV OR $02 (M3 set, the other bits kept)', 'RG1SAV AND $E7 (bits 4 and 3 cleared)', 'A = the new RG6SAV, F = $00, BC = $0007, DE = $7F03 and HL = $F3D1 (just past GRPPAT)')
