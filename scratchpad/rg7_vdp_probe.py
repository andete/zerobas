#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RG7: the VDP's OWN register 7 (not RG7SAV) after `COLOR 15,4,7`, per mode.
rg7_probe.out: RG7SAV is FORCLR*16+BDRCLR in every mode on zerobas; the VG-8020
has FORCLR*16+BAKCLR in SCREEN 0 and BDRCLR alone in 1..3. In SCREEN 0 the low
nibble is the visible background. A program ends in `GOTO` itself; a Tcl timer
reads `debug read {VDP regs} 7` while it spins. Prediction: SCREEN 0 -> VG 244,
ZB 247 (a VISIBLE background difference); SCREEN 2 -> VG 7, ZB 247.
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

CASES = {"s0": "10 SCREEN 0:COLOR 15,4,7:GOTO 10",
         "s2": "10 SCREEN 2:COLOR 15,4,7:GOTO 10"}
for name, line in CASES.items():
    for m in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
        fd, path = tempfile.mkstemp(suffix=".txt", prefix="rg7v_")
        os.close(fd)
        os.unlink(path)
        pro = (f"after time 30 {{ set f [open {{{path}}} w]; puts $f [debug read {{VDP regs}} 7]; close $f }}",)
        omsx_repl.run_cases(m, [("direct", ["NEW", line, "RUN"])], batch=False,
                            reset=("", "SCREEN 0"), run_gap=25.0, prologue=pro)
        v = open(path).read().strip() if os.path.exists(path) else "NO READING"
        print(f"ROW {name} {m} VDP R#7 = {v}", flush=True)
