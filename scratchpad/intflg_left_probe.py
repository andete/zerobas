#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3f): what does BASIC leave in INTFLG ($FC9B) after it has handled a
CTRL-STOP itself -- VG-8020 against zerobas?

INTFLG is a LATCH on both machines (intflg_isr_run6.out). The VG-8020's interpreter
consumes it between statements; zerobas's BASIC reads the key on its own and never
looks at INTFLG. If ours leaves it set, a LATER ISCNTC (a BLOADed program's pause key)
sees a press that BASIC already handled. ON STOP GOSUB + STOP ON takes the press (no
break); once the handler has run and the key is up, the program prints INTFLG.

    python3 -u scratchpad/intflg_left_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

# (a 250-tick loop outlasted the capture: no row on either machine.) Loop until the
# handler has fired, then 1 s more -- the key is up by then -- then print.
PROG = ['C=0:ON STOP GOSUB 70:STOP ON', 'IF C=0 THEN 20',
        'T=TIME:STOP OFF', 'IF TIME-T<50 THEN 40',
        'PRINT"[L";C>0;PEEK(&HFC9B);"]"', 'END', 'C=C+1:RETURN']
CTRL_STOP = ((6, 0x02), (7, 0x10))


def main():
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
        raw = omsx_repl.run_cases(mach, [("stored", PROG)], batch=False, holds=[CTRL_STOP],
                                  hold_lead=0.5, hold_secs=1.0)[0]
        txt = " ".join("".join(raw or "").split())
        i = txt.rfind("[L ")
        print(f"{mach:28} {txt[i:i + 30] if i >= 0 else '<NO ROW> ' + txt[-100:]!r}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
