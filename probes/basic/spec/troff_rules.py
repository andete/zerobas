#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/keywords/TROFF.md's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md): TROFF --
probes/basic/spec/ktron.py (the loader is ktron_model; the interpreter is kstop_model's small BASIC)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktron_model as M  # noqa: E402

PAGE = "docs/keywords/TROFF.md"
OUTPUTS = M.OUTPUTS
OUTPUTS_DESC = M.OUTPUTS_DESC


def cases():
    return M.load("TROFF")


RULES = M.rules("TROFF")
