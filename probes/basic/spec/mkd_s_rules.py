#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/keywords/MKD$.md's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md): MKD$ --
probes/basic/spec/kmkcv.py (the loader and the model are kmkcv_model)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kmkcv_model as M  # noqa: E402

PAGE = "docs/keywords/MKD$.md"
OUTPUTS = M.OUTPUTS
OUTPUTS_DESC = M.OUTPUTS_DESC


def cases():
    return M.load("MKD$")


RULES = M.rules("MKD$")
