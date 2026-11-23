#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/keywords/MID$.md's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md): MID$ --
probes/basic/spec/kslice.py (the loader and the model are kslice_model)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kslice_model as M  # noqa: E402

PAGE = "docs/keywords/MID$.md"
OUTPUTS = M.OUTPUTS
OUTPUTS_DESC = M.OUTPUTS_DESC


def cases():
    return M.load("MID$")


RULES = M.mid_rules("1. MID$(a$, P [, M]) -- the function")
