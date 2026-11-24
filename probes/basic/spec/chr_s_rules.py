#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/keywords/CHR$.md's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md): CHR$ --
probes/basic/spec/kstr.py (the loader and the model are kstr_model)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kstr_model as M  # noqa: E402

PAGE = "docs/keywords/CHR$.md"
OUTPUTS = M.OUTPUTS
OUTPUTS_DESC = M.OUTPUTS_DESC


def cases():
    return M.load("CHR$")


RULES = M.rules("CHR$")
