#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/keywords/DEFSTR.md's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md): DEFSTR --
probes/basic/spec/kdeftype.py (the loader and the interpreter model are kdeftype_model)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kdeftype_model as M  # noqa: E402

PAGE = "docs/keywords/DEFSTR.md"
OUTPUTS = M.OUTPUTS
OUTPUTS_DESC = M.OUTPUTS_DESC


def cases():
    return M.load("DEFSTR")


RULES = M.rules("DEFSTR", cases()["ref"])
