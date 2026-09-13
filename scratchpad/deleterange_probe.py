#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWBREADTH batch 3 — what does DELETE of an EXISTING line do MID-PROGRAM?

The `deletekw` row scores only the FAILURE path (`DELETE 99`, no line 99 ->
Illegal function call). The SUCCESS path is unexercised, and a breadth row needs
to know whether execution CONTINUES after a successful DELETE: if it does not,
nothing can be read afterwards and the row cannot carry a VALUE.

⚠️ MEASURED IN ISOLATION FIRST, AND THE FILE ITSELF SAYS WHY. Directly below
`deletekw` in basic_probe_kwsweep.py is the note that `AUTO` left the machine in
LINE-ENTRY MODE and swallowed the input of 21 FOLLOWING rows (0 divergent ->
DIVERGENT=22 + UNREADABLE=1). DELETE mutates the running program the same way, so
it is characterised here before any row goes near the sweep.

RAM at $E002 carries the flag because RUN CLEARS VARIABLES (the `runkw` lesson);
$E001 is the cell `runkw` already uses, so this takes the next one.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "probes", "lib"))
import omsx_repl                                                    # noqa: E402

CASES = {
    # (1) does a line AFTER the DELETE still run at all?
    "after": ['10 POKE&HE002,0', '20 DELETE 40',
              '30 PRINT"[A";PEEK(&HE002);"]"', '40 REM', 'RUN'],
    # (2) did the DELETE actually remove line 40? gone -> Undefined line number
    "gone":  ['10 POKE&HE002,0', '20 DELETE 40', '30 GOTO 40',
              '40 PRINT"[G9]"', 'RUN'],
    # (3) the control: same shape, NO delete, so line 40 must be reached
    "ctl":   ['10 POKE&HE002,0', '20 GOTO 40', '30 END',
              '40 PRINT"[C9]"', 'RUN'],
    # (4) a RANGE over lines that exist
    "range": ['10 POKE&HE002,0', '20 DELETE 30-40',
              '25 PRINT"[R";PEEK(&HE002);"]"', '30 REM', '40 REM', 'RUN'],
}

# 🔴 THE CF-3300 NEEDS `SCREEN 0` IN ITS RESET AND THE FIRST RUN OF THIS PROBE DID
# NOT GIVE IT ONE. A stock MSX1 boots SCREEN 1, and omsx_repl's scrape assumes
# SCREEN 0 (40 cols at 0x0000), so the capture came back as the PATTERN GENERATOR
# TABLE read as text -- ' p p x ` @ 0` ...' for all four cases, identically.
# 🎯 THE INSTRUMENT SAID SO RATHER THAN HANDING ME A PLAUSIBLE STRING: it printed
# "all 8 echo slots read BLIND/mode (SCRMOD != 0) ... a scrape of the wrong VRAM
# plane". The values are `basic_probe_kwsweep`'s own MACH_BOOT/MACH_RESET_PRE, and
# the two tables disagreeing is exactly what this probe reproduced by inventing
# its own.
MACHINES = [("Philips_VG_8020", 8.0, ("NEW", "CLS")),
            ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW", "CLS")),
            ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0, ("NEW", "CLS"))]

for machine, boot, reset in MACHINES:
    print(f"=== {machine} ===", flush=True)
    for key, lines in CASES.items():
        caps = omsx_repl.run_cases(
            machine, [(key, list(reset) + lines)],
            batch=False, boot=boot, step=3.0, cap_gap=8.0, timeout=300.0)
        text = " ".join(str(caps[0]).split())
        print(f"  {key:6} {text[-180:]!r}", flush=True)
