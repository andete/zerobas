#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/keywords/IF.md's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md): IF --
probes/basic/spec/kif.py (the loader and the model are kif_model)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kif_model as M  # noqa: E402

PAGE = "docs/keywords/IF.md"
OUTPUTS = M.OUTPUTS
OUTPUTS_DESC = M.OUTPUTS_DESC


def cases():
    return M.load("IF")


RULES = M.rules("IF")
