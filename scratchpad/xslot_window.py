#!/usr/bin/env python3
"""D-XSLOTPRICE 0b -- name the spin control's outcome instead of leaving it blank."""
from __future__ import annotations
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402
ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
CASES = [
    ("spin2000", ["10 T=TIME", "20 FOR I=1 TO 2000:NEXT",
                  '30 PRINT "[";TIME-T;"]"', "RUN"]),
    ("spin2000.nofor", ["10 T=TIME", "20 I=0",
                        "30 I=I+1:IF I<2000 THEN 30",
                        '40 PRINT "[";TIME-T;"]"', "RUN"]),
]
def main() -> int:
    caps = omsx_repl.run_cases(ZB, CASES, batch=False, reset=(), boot=8.0,
                               step=3.0, cap_gap=60.0, timeout=900.0)
    for (name, _), cap in zip(CASES, caps):
        scr = re.sub(r"\s+", " ", cap or "").strip()
        print(f"--- {name}\n    {scr[-260:]!r}")
    return 0
if __name__ == "__main__":
    sys.exit(main())
