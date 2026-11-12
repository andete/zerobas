#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG / STRTMS: PLYCNT ($FB40) and MUSICF ($FB3F) around BASIC PLAY statements --
the VG-8020's PLAY = "PLYCNT + 1, then STRTMS" model, checked: right after a short PLAY,
after a second PLAY queued behind a long note, and after a PLAY longer than the ring
(the statement returns only once its tail fits). Black-box: work-area RAM.

    python3 -u scratchpad/plycnt_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

SHOW = 'PRINT "[C";A;B;C;D;"]"'
CASES = {
    "short":  ['PLAY "C":A=PEEK(&HFB40):B=PEEK(&HFB3F):C=0:D=0', SHOW],
    "behind": ['PLAY "T32L1C":A=PEEK(&HFB40):B=PEEK(&HFB3F):PLAY "D":C=PEEK(&HFB40):D=PEEK(&HFB3F)', SHOW],
    "two_bh": ['PLAY "T32L1C":PLAY "D":PLAY "E":A=PEEK(&HFB40):B=PEEK(&HFB3F):C=0:D=0', SHOW],
    "long":   ['PLAY "T255L64CDEFGABCDEFGABCDEFGABCDEFGABCDEFGABCDEFGAB":A=PEEK(&HFB40):B=PEEK(&HFB3F):C=0:D=0', SHOW],
    # ROUND 2: do voices B and C get an end marker from `PLAY "C"`? (their PUT pointers)
    "bc_put": ['PLAY "C":A=PEEK(&HF95F):B=PEEK(&HF965):C=PEEK(&HF959):D=0', SHOW],
    "after":  ['PLAY "C":T=TIME', "IF TIME-T<60 THEN 20", 'A=PEEK(&HFB40):B=PEEK(&HFB3F):C=0:D=0', SHOW],
}


def main():
    names = sys.argv[1:] or list(CASES)
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
        raws = omsx_repl.run_cases(mach, [("stored", CASES[n]) for n in names],
                                   batch=False, run_gap=12.0)
        for n, raw in zip(names, raws):
            txt = " ".join("".join(raw or "").split())
            i = txt.rfind("[C")
            print(f"{mach[:10]:10} {n:7} {txt[i:i + 20] if i >= 0 else '<NO [C>'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
