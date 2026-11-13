#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ROBOREG: a disk's boot on both machines as a time series -- PC, CURLIN, screen mode
and the screen's text every N seconds, to find the first point zerobas and the CF-3300
part. Reuses diskcorpus_run.run_one (the image is RUN, never decoded; black-box: registers,
the CURLIN work-area cell, VRAM).

    DISKCORPUS_DIR=... python3 -u scratchpad/roboseries_probe.py IMAGE [STEP] [END]
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import diskcorpus_run as D  # noqa: E402


def main():
    img = os.path.join(os.environ["DISKCORPUS_DIR"], sys.argv[1])
    step = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    end = float(sys.argv[3]) if len(sys.argv) > 3 else 44.0
    start = float(sys.argv[4]) if len(sys.argv) > 4 else step
    times = [round(start + step * k, 3) for k in range(0, int((end - start) / step) + 1)]
    for side, mach in (("REF", D.REF), ("ZB", D.ZB)):
        caps = D.run_one(mach, img, times) or {}
        for t in times:
            c = caps.get(f"T{t:g}")
            if not c:
                print(f"{side} T{t:6} <none>")
                continue
            txt = " / ".join(D.screen_text(c))[:90]
            print(f"{side} T{t:6} pc={c['pc']:04X} curlin={c['curlin']:5} {D.mode_of(c['regs'])} {txt}",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
