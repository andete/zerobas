#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Does a running program PAUSE on the STOP key (INTFLG 4) -- VG-8020 against zerobas?
A loop runs ~3 s by TIME and prints; STOP tapped once (0.3 s) about RUN + 1 s. A machine
that pauses until a second STOP never prints within the window; one that does not, does.
Stored program; black-box: the screen.

    python3 -u scratchpad/stoppause_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

# TIMELINE (omsx_repl): the press lands at RUN + step 3 + lead 0.5 = RUN+3.5 s, held 1 s,
# the capture at ~RUN+5.5 s. A 3 s loop ended before the press (stoppause_run.out: DONE on
# both); a 5 s one outlasted the capture (stoppause_run2.out: nothing on both). 4.5 s
# (225 ticks at 50 Hz) separates them: no pause -> DONE at RUN+4.5; a pause -> nothing.
PROG = ['T=TIME', 'IF TIME-T<225 THEN 20', 'PRINT "[D DONE]"']


def main():
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
        scr = omsx_repl.run_cases(mach, [("stored", PROG)], batch=False,
                                  reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                  holds=[((7, 0x10),)], hold_lead=0.5, hold_secs=1.0)[0]   # 0.2 / 0.3 s: DONE on both (stoppause_run.out)
        rows = [scr[i:i + 40].strip() for i in range(0, len(scr or ""), 40)]
        keep = [x for x in rows if x.startswith("[D") or "Break" in x]
        print(f"{mach[:10]:10} {' | '.join(keep) or '<NO OUTPUT>'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
