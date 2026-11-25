#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/keywords/DATA.md's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md): DATA --
probes/basic/spec/kdata.py (the loader is kdata_model; the interpreter is kstop_model's small BASIC)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kdata_model as M  # noqa: E402

PAGE = "docs/keywords/DATA.md"
OUTPUTS = M.OUTPUTS
OUTPUTS_DESC = M.OUTPUTS_DESC


def cases():
    return M.load("DATA")


RULES = M.rules("DATA")
