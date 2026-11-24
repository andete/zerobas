#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/keywords/MOD.md's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md): MOD --
probes/basic/spec/kops.py (the loader and the model are kops_model)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kops_model as M  # noqa: E402

PAGE = "docs/keywords/MOD.md"
OUTPUTS = M.OUTPUTS
OUTPUTS_DESC = M.OUTPUTS_DESC


def cases():
    return M.load("MOD")


RULES = M.rules("MOD")
