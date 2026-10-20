#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EVALSLOPE apparatus check (2026-10-20): input-devices-acceptance phase C's `up` case
reads MIS-ECHOED ('RUN' -> 'UN') on the build with the one-loop climber, and passes on
a39cefcc. The echo dump is taken 0.8 s after RUN; the key goes down 0.3 s after it. How
long does the phase's sampling loop run (TIME ticks, 1/50 s), with nothing held, on the
machine as installed? Run once per build. Prints [ticks].
    python3 -u scratchpad/stickloop_time_probe.py        (STL_MACHINE to override)
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

M = os.environ.get("STL_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
BODY = ["T=TIME:A=0:C=0", "FOR I=1 TO 60", "B=STICK(0):IF B<>0 THEN A=B",
        "D=STRIG(0):IF D<>0 THEN C=D", "NEXT", 'PRINT"[";TIME-T;"]"']


def main():
    raws = omsx_repl.run_cases(M, [("stored", BODY)] * 2, reset=("NEW", "CLS"),
                               cap_gap=25.0, batch=False)
    for r in raws:
        v = re.findall(r"\[\s*(-?\d+)\s*\]", (r or "").replace("\n", ""))
        print(f"{M}: [{v[-1] if v else 'NO READING'}] ticks", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
