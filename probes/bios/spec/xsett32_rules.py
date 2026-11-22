#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/SETT32.md's EXECUTABLE RULES (docs/spec-method.md §3a): SETT32 ($007B) -- the run the SETxxx calls share
(probes/bios/spec/xset.asm, op 1; the loader, the model and the rules are xset_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xset_model as X  # noqa: E402

PAGE = "docs/bios/SETT32.md"
OUTPUTS = X.OUTPUTS


def cases():
    return X.load(1)


S1 = "1. SETT32 ($007B): set the VDP up for 32-column text"
RULES = X.rules(1, "T3", S1, 'RG0SAV AND $01 (only bit 0 kept)', 'RG1SAV AND $E7 (bits 4 and 3 cleared: graphic 1)', 'A = the new RG6SAV, F = $00, BC = $0007, DE = $0000 and HL = $F3C7 (just past T32PAT)')
