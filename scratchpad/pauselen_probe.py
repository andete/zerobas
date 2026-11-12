#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BRKLATCH, before resuming: the STOP pause against the PRESS LENGTH -- VG-8020 against
zerobas. A 4 s TIME loop (200 ticks at 50 Hz), then PRINT. The press lands at RUN + step
3 + lead 0.5 = RUN+3.5 s and the capture at RUN+4.5+h, so for each hold h: no pause ->
DONE (by RUN+4); a pause the RELEASE ends -> DONE (about RUN+3.5+h, before the capture);
a pause that waits for a SECOND press -> nothing. Stored program; black-box: the screen.

    python3 -u scratchpad/pauselen_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

PROG = ['T=TIME', 'IF TIME-T<200 THEN 20', 'PRINT "[D DONE"; TIME-T;"]"']
HOLDS = (0.2, 0.5, 1.0, 2.0)


def main():
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
        for h in HOLDS:
            scr = omsx_repl.run_cases(mach, [("stored", PROG)], batch=False,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                      holds=[((7, 0x10),)], hold_lead=0.5, hold_secs=h)[0]
            rows = [scr[i:i + 40].strip() for i in range(0, len(scr or ""), 40)]
            keep = [x for x in rows if x.startswith("[D") or "Break" in x]
            print(f"{mach[:10]:10} hold {h:3.1f} s  {' | '.join(keep) or '<NO OUTPUT>'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
