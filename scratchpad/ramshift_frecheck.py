#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RAMSHIFT: boot FRE(0) on all four machines (SCREEN 0 first: the CF-3300
boots in SCREEN 1, which the screen reader cannot parse). Output:
scratchpad/ramshift_disk.out. Prediction (2026-10-13): diskless -4360 against
the VG-8020; the disk build 275 AHEAD of the CF-3300 (it was 343 short).
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl
for m in ("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
    raw = omsx_repl.run_cases(m, [("direct", ["SCREEN 0", 'PRINT"[";FRE(0);"]"'])], batch=False, reset=("",), run_gap=6.0)[0]
    print(f"{m:30s} boot FRE(0) = {omsx_repl.result_span(raw)}")
