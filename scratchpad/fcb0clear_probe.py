#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TAPELOAD lead (2026-10-14): where does channel #0's block sit after
`CLEAR n,top`? A tape loader of the shape `CLEAR 0,&H83F0:BLOAD"CAS:",R:
BLOAD"CAS:",R` loads ~24 KB from &H83F0 up and then searches the tape again
through channel #0's buffer. On the reference everything BASIC keeps moves below
the new HIMEM; if zerobas leaves channel #0 high, the load overwrites it.
Prediction: VG-8020 VARPTR(#0) < &H83F0 after the CLEAR; zerobas above &HE000.
Typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

CASES = {
    "boot": ['PRINT "[";HEX$(VARPTR(#0));"]"'],
    "clear": ['CLEAR 50,&H83F0:PRINT "[";HEX$(VARPTR(#0));"]"'],
    "himem": ['CLEAR 50,&H83F0:PRINT "[";HEX$(PEEK(&HFC4A)+256*PEEK(&HFC4B));"]"'],
}
for name, lines in CASES.items():
    out = {}
    for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
        scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                  reset=("", "SCREEN 0:WIDTH 40"), step=3.0)[0] or ""
        rows = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
        out[side] = " | ".join(r for r in rows if r.startswith("[") or "rror" in r)
    print(f"ROW {name} VG=[{out['VG']}] ZB=[{out['ZB']}] {'SAME' if out['VG'] == out['ZB'] else 'DIVERGES'}",
          flush=True)
