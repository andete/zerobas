#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWTIER1 — is `CLEAR n,himem` safe to make a sweep row, and what does it read?

CLEAR's third form sets the top of memory BASIC may use (`HIMEM`, $FC4A, declared
in basic/sysvars.inc). Two hazards have to be settled BEFORE a row is written:

  1. the row LOWERS a global ceiling, so every row after it runs with less memory
     unless the original is put back -- the `AUTO` hazard, which once cost 21 rows;
  2. `CLEAR` WIPES VARIABLES, so the original cannot be saved in one -- the
     `MAXFILES` trap, where the restore destroyed the value it was protecting.

So the original is parked in RAM at $E003/$E004 (above the lowered ceiling, where
BASIC will not touch it; $E001 is runkw's cell and $E002 deleterange_probe's).

⚠️ Reuses basic_probe_kwsweep's own MACH_BOOT / MACH_RESET_PRE.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "probes", "lib"))
import omsx_repl                                                    # noqa: E402

H = 'PEEK(&HFC4A)+256*PEEK(&HFC4B)'
CASES = {
    # what is HIMEM at rest?
    "rest":    [f'10 PRINT"[R";{H};"]"', 'RUN'],
    # does `CLEAR n,himem` set it?
    "set":     ['10 CLEAR 100,&HD000', f'20 PRINT"[S";{H};"]"', 'RUN'],
    # park the original, lower it, then put it back -- is it restored EXACTLY?
    # 🔴 THE RESTORE STATEMENT IS 39 CHARS AND `as_stored` PACKS BODIES TO <=34, so
    # a sweep row cannot carry it whole. This case checks the two-statement form --
    # does `CLEAR 100,B` still see B, given CLEAR WIPES VARIABLES? The argument must
    # be evaluated before the clear takes effect, and that is measured, not assumed.
    "split":   ['10 POKE&HE003,PEEK(&HFC4A):POKE&HE004,PEEK(&HFC4B)',
                '20 CLEAR 100,&HD000',
                '30 B=PEEK(&HE003)+256*PEEK(&HE004)',
                '40 CLEAR 100,B',
                f'50 PRINT"[U";{H};"]"', 'RUN'],
    "restore": ['10 POKE&HE003,PEEK(&HFC4A):POKE&HE004,PEEK(&HFC4B)',
                '20 CLEAR 100,&HD000',
                '30 CLEAR 100,PEEK(&HE003)+256*PEEK(&HE004)',
                f'40 PRINT"[T";{H};"]"', 'RUN'],
}

MACHINES = [("Philips_VG_8020", 8.0, ("NEW", "CLS")),
            ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW", "CLS")),
            ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0, ("NEW", "CLS"))]

for machine, boot, reset in MACHINES:
    print(f"=== {machine} ===", flush=True)
    for key, lines in CASES.items():
        caps = omsx_repl.run_cases(
            machine, [(key, list(reset) + lines)],
            batch=False, boot=boot, step=3.0, cap_gap=8.0, timeout=300.0)
        print(f"  {key:8} {' '.join(str(caps[0]).split())[-70:]!r}", flush=True)
