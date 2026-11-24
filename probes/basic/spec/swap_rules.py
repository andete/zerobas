#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/keywords/SWAP.md's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md): SWAP --
probes/basic/spec/klet.py (the loader and the model are klet_model)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import klet_model as M  # noqa: E402

PAGE = "docs/keywords/SWAP.md"
OUTPUTS = M.OUTPUTS
OUTPUTS_DESC = M.OUTPUTS_DESC


def cases():
    return M.load("SWAP")


RULES = M.rules("SWAP")
