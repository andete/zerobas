#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""K-BANNER — cut `show_title` and require the banner gate to go RED.

A gate that has never failed is not known to be able to. The cut is the exact
thing the gate exists to catch: `call show_title` in `basic/interp.asm`'s init,
neutralised. The banner disappears; the program's own marker still prints, so
this separates "the header stopped reaching the screen" (RED, the finding) from
"the machine never booted" (rc 2, an instrument fault).

🔴 RESTORE IS `atexit`, AND THE MTIME IS DELIBERATELY *NOT* PRESERVED
(D-KNIFEGUARD). A knife that puts the mtime back leaves `make` with nothing to
rebuild, and the next gate then scores the KNIFED ROM as if it were the shipping
one. Content restored byte-identically; mtime left bumped so the rebuild happens.
"""
from __future__ import annotations

import atexit
import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 🔴 THE FIRST CUT WAS `call show_title` IN interp.asm's INIT, AND IT WAS THE
# WRONG KNIFE: the machine did not reach BASIC at all -- the capture was a screen
# of GARBAGE, banner AND marker gone. The cause is one line into the body: it
# opens with `call INITXT`, which puts the VDP in SCREEN 0 text mode. Removing
# the call removed the mode set, so that cut tested "no text mode", not "no
# header" -- and the gate rightly refused to call it a verdict (rc 2).
# The surgical cut KEEPS `INITXT` and returns before the print loop: the boot
# completes, the marker still prints, and only the header is gone.
SRC = ROOT / "basic" / "title-body.inc"
CUT = "                ld      hl,banner_text"
WITH = "                ret                     ; K-BANNER CUT\n" + CUT


def main() -> int:
    orig = SRC.read_text()
    if CUT not in orig:
        print(f"INSTRUMENT FAULT: the anchor {CUT.strip()!r} is not in "
              f"{SRC.relative_to(ROOT)} -- the knife would cut NOTHING and the "
              f"red arm would pass by never firing.")
        return 2
    digest = hashlib.sha256(orig.encode()).hexdigest()

    def restore():
        SRC.write_text(orig)
        assert hashlib.sha256(SRC.read_text().encode()).hexdigest() == digest, \
            "basic/interp.asm was NOT restored!"
        print(f"  restored {SRC.relative_to(ROOT)} byte-identically")
    atexit.register(restore)

    SRC.write_text(orig.replace(CUT, WITH, 1))
    print("K-BANNER: the title body returns before its print loop "
          "(INITXT kept); rebuilding and re-running the gate")
    r = subprocess.run(["make", "repack-machine"], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"INSTRUMENT FAULT: the KNIFED tree does not build:\n"
              f"{(r.stdout + r.stderr)[-1200:]}")
        return 2
    g = subprocess.run([sys.executable,
                        str(ROOT / "probes/basic/basic_probe_banner.py"), "--gate"],
                       cwd=ROOT, capture_output=True, text=True)
    out = g.stdout + g.stderr
    print(out.rstrip())
    if g.returncode == 1 and "are GONE" in out:
        print("\n✅ K-BANNER: the gate went RED for the right reason "
              "(marker printed, header absent).")
        return 0
    if g.returncode == 2:
        print("\n🔴 K-BANNER INCONCLUSIVE: the gate reported an instrument "
              "fault, not a banner failure -- the cut proved nothing.")
        return 1
    print(f"\n🔴 K-BANNER FAILED: the gate returned {g.returncode} with the "
          f"banner CUT. It cannot detect the thing it exists to detect.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
