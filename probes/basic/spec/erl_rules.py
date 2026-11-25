#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/keywords/ERL.md's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md): ERL --
probes/basic/spec/kerr.py (the loader is kerr_model; the interpreter is kstop_model's small BASIC)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kerr_model as M  # noqa: E402

PAGE = "docs/keywords/ERL.md"
OUTPUTS = M.OUTPUTS
OUTPUTS_DESC = M.OUTPUTS_DESC


def cases():
    return M.load("ERL")


RULES = M.rules("ERL")
