#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TAPELOAD (2026-10-16, Head over Heels `Out of memory in 40`): how much free
memory is left when a GOSUB is refused, on each machine? zerobas refuses a frame
unless CTL_FRAME_MARGIN (768 B) stays clear; Head over Heels' line 40 had 671 B.
Recurse with GOSUB until Out of memory, then print the depth reached and FRE(0)
(read with the frames still standing), under two string-space sizes.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "probes", "lib"))
import omsx_repl

CASES = {
    "c200": ["NEW", "10 CLEAR 200:ON ERROR GOTO 100:D=0:F=0", "20 D=D+1:GOSUB 20",
             '100 F=FRE(0):PRINT"[D";D;F;"]":END', "RUN"],
    "himem": ["NEW", "10 CLEAR 200,&H9800:ON ERROR GOTO 100:D=0:F=0", "20 D=D+1:GOSUB 20",
              '100 F=FRE(0):PRINT"[D";D;F;"]":END', "RUN"],
    # after the trapped overflow: does a RETURN still find a frame? (VG-8020's FRE
    # in the handler reads nearly full memory: the frames look discarded)
    "ret": ["NEW", "10 CLEAR 200:ON ERROR GOTO 100:D=0", "20 D=D+1:GOSUB 20",
            '100 PRINT"[R";ERR;"]";:RETURN', "RUN"],
    # and a plain trapped error inside ONE GOSUB: is that frame kept?
    "one": ["NEW", "10 ON ERROR GOTO 100", '20 GOSUB 50:PRINT"[BACK]":END', "50 ERROR 5",
            "60 RETURN", "100 RESUME 60", "RUN"],
}
for name, prog in CASES.items():
    for m in ("C-BIOS_MSX1_EU_REPACK_NODISK", "Philips_VG_8020"):
        scr = omsx_repl.run_cases(m, [("direct", prog)], batch=False,
                                  reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=60.0)[0]  # 30 s ran out at ~4000 frames (2026-10-17)
        r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)] if scr else ["<NO OUTPUT>"]
        keep = [x for x in r if x.startswith("[") or "rror" in x or "memory" in x or "GOSUB" in x]
        print(f"{name:6} {m:30} {' | '.join(keep) or '<nothing matched>'}", flush=True)
