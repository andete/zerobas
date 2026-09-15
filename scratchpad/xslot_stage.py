#!/usr/bin/env python3
"""D-XSLOTPRICE 0b -- staged diagnostic: which step stops answering?

Each case is its own boot. Every case prints its own fence, so a silent case is
a silent STEP, not a silent probe.
"""
from __future__ import annotations
import os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"

CASES = [
    # (name, lines) -- each ends with RUN
    ("ctl.nohook", [
        '10 PRINT "[";1+1;"]"',
        "RUN",
    ]),
    ("arm0", [                       # N=0: hook entered, no inter-slot call
        "10 POKE &HE771,0",
        '20 X=CVI("AB")',
        '30 PRINT "[";PEEK(&HE770);"]"',
        "RUN",
    ]),
    ("arm1", [                       # exactly ONE inter-slot call
        "10 POKE &HE771,1",
        '20 X=CVI("AB")',
        '30 PRINT "[";PEEK(&HE770);"]"',
        "RUN",
    ]),
    ("arm64", [                      # 64 inter-slot calls in one hook entry
        "10 POKE &HE771,64",
        '20 X=CVI("AB")',
        '30 PRINT "[";PEEK(&HE770);"]"',
        "RUN",
    ]),
]


def main() -> int:
    caps = omsx_repl.run_cases(ZB, CASES, batch=False, reset=(), boot=8.0,
                               step=3.0, cap_gap=20.0, timeout=900.0)
    import re
    rc = 0
    for (name, _), cap in zip(CASES, caps):
        scr = cap or ""
        m = re.search(r"\[\s*(-?\d+)\s*\]", scr)
        val = m.group(1) if m else None
        print(f"{name:12s} -> {val if val is not None else '<NO FENCE>'}")
        if val is None:
            rc = 1
    print()
    print("ctl.nohook must print 2 -- it proves the rig, and it touches no hook.")
    print("arm0 prints whatever $E770 last held (no call ran); arm1/arm64 must")
    print("print 16 (main's $4002). 52 would mean the disk ROM stayed mapped.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
