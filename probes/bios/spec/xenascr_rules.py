#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/ENASCR.md's EXECUTABLE RULES (docs/spec-method.md §3a): ENASCR ($0044) -- the run docs/bios/WRTVDP.md
reads (probes/bios/spec/xvdpreg.asm, op 2; the loader is xwrtvdp_rules.load, the shared rules xdisscr_rules.screen)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xwrtvdp_rules as W  # noqa: E402
import xdisscr_rules as D  # noqa: E402

PAGE = "docs/bios/ENASCR.md"
OUTPUTS = W.OUTPUTS


def cases():
    return W.load(2)


S1 = "1. ENASCR ($0044): show the screen"
RULES = D.screen("ES", S1, lambda v: v | 0x40, "with bit 6 (the screen-enable bit) set")
