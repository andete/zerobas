#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/keywords/RETURN.md's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md): RETURN --
probes/basic/spec/kgosub.py (the loader and the model are kgosub_model)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kgosub_model as M  # noqa: E402

PAGE = "docs/keywords/RETURN.md"
OUTPUTS = M.OUTPUTS
OUTPUTS_DESC = M.OUTPUTS_DESC


def cases():
    return M.load("RETURN")


RULES = M.rules("RETURN")
