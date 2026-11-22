#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/SETTXT.md's EXECUTABLE RULES (docs/spec-method.md §3a): SETTXT ($0078) -- the run the SETxxx calls share
(probes/bios/spec/xset.asm, op 0; the loader, the model and the rules are xset_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xset_model as X  # noqa: E402

PAGE = "docs/bios/SETTXT.md"
OUTPUTS = X.OUTPUTS


def cases():
    return X.load(0)


S1 = "1. SETTXT ($0078): set the VDP up for 40-column text"
RULES = X.rules(0, "TX", S1, 'RG0SAV AND $01 (only bit 0 kept)', '(RG1SAV AND $E7) OR $10 (bits 4 and 3 the mode: M1 set)', 'A = the new RG6SAV, F = $00, BC = $0007, DE = $0000 and HL = $F3BD (just past TXTPAT)')
