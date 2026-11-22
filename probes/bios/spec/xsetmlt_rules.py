#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/SETMLT.md's EXECUTABLE RULES (docs/spec-method.md §3a): SETMLT ($0081) -- the run the SETxxx calls share
(probes/bios/spec/xset.asm, op 3; the loader, the model and the rules are xset_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xset_model as X  # noqa: E402

PAGE = "docs/bios/SETMLT.md"
OUTPUTS = X.OUTPUTS


def cases():
    return X.load(3)


S1 = "1. SETMLT ($0081): set the VDP up for multicolour"
RULES = X.rules(3, "MT", S1, 'RG0SAV AND $01 (only bit 0 kept)', '(RG1SAV AND $E7) OR $08 (M2 set)', 'A = the new RG6SAV, F = $00, BC = $0007, DE = $0000 and HL = $F3DB (just past MLTPAT)')
