#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/keywords/LIST.md's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md): LIST --
probes/basic/spec/klist.py (the loader is klist_model; the interpreter is kstop_model's small BASIC)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import klist_model as M  # noqa: E402

PAGE = "docs/keywords/LIST.md"
OUTPUTS = M.OUTPUTS
OUTPUTS_DESC = M.OUTPUTS_DESC


def cases():
    return M.load("LIST")


RULES = M.rules("LIST")
