#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GATEBLIND -- run JUST phase A, so a knife can score the clip rows without
paying for all 356. Imports the gate's own phase, never a copy."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
from basic_probe_graphics import phase_a          # noqa: E402
raise SystemExit(0 if phase_a() == 0 else 1)
