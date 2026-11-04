#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LPTERRNL, measure first (2026-11-05): who ends the printer line on an error.

Our own programs, one per boot; openMSX's printer logger captures what the
printer receives (CR / LF shown as \\r \\n). Typed BASIC in, the log out.

    python3 -u scratchpad/lpterrnl_probe.py [vg8020,zb]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402
from basic_probe_editverb import prn_reading       # noqa: E402

H = "10 ON ERROR GOTO 90"
CASES = {
    # the error INSIDE the LPRINT; the handler LPRINTs
    "inlp":   [H, '20 LPRINT "A[";1/0', "30 END", '90 LPRINT "E";ERR:RESUME 30'],
    # the error in the NEXT statement, after an LPRINT that ended with ;
    "after":  [H, '20 LPRINT "A[";:X=1/0', "30 END", '90 LPRINT "E";ERR:RESUME 30'],
    # the handler prints NOTHING to the printer; the program LPRINTs after
    "quiet":  [H, '20 LPRINT "A[";1/0', '30 LPRINT "Z":END', "90 RESUME 30"],
    "quiet2": [H, '20 LPRINT "A[";:X=1/0', '30 LPRINT "Z":END', "90 RESUME 30"],
    # untrapped
    "untrap": ['20 LPRINT "A[";1/0'],
    # control: no error at all
    "ctrl":   ['20 LPRINT "A[";:LPRINT "Z"'],
}
SIDES = {"vg8020": ("Philips_VG_8020", 8.0), "zb": ("C-BIOS_MSX1_EU_REPACK_NODISK", 8.0)}


def main():
    sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,zb").split(",")
    for side in sides:
        m, boot = SIDES[side]
        log = probe_tmp.tmp(f"lpterrnl_{side}.log")
        plug = (f"set printerlogfilename {{{log}}}", "plug printerport logger")
        cases = [("direct", ["NEW"] + lines + ["RUN"]) for lines in CASES.values()]
        caps = omsx_repl.run_cases(m, cases, batch=False, reset=(), boot=boot, step=4.0,
                                   prologue=plug, capture=("screen_printer", log))
        for name, raw in zip(CASES, caps):
            print(f"{side:7s} {name:7s} {prn_reading(raw)}", flush=True)
    print(__import__("probe_refcache").summary())


if __name__ == "__main__":
    main()
