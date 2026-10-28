#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""OPEN twice, the exact rule (Joost 2026-10-27): before keeping the TYPED case in a
channel's FCB, measure what case reaches the DISK on the CF-3300 and whether a
lower-case name finds an upper-case file. Each case runs on a fresh copy of
disk/test720.dsk; typed BASIC in, the screen out.
    python3 -u scratchpad/fcbcase_probe.py [MACHINE ...]
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

CASES = {
    "save_lc_files": ["NEW", "10 REM", 'SAVE"ts.dat"', 'FILES"*.DAT"'],
    "load_lc":       ["NEW", "10 REM", 'SAVE"TS.DAT"', "NEW", 'LOAD"ts.dat"', "LIST"],
    "open_lc_files": ['OPEN"ab.txt"FOR OUTPUT AS 1:PRINT#1,"X":CLOSE', 'FILES"*.TXT"'],
    "open_case2":    ['OPEN"TS.DAT"FOR OUTPUT AS 1:PRINT#1,"X":CLOSE', 'OPEN"TS.DAT"FOR INPUT AS 1',
                      'OPEN"ts.dat"FOR INPUT AS 2', 'PRINT "K";ERR', "CLOSE"],
}
MACHINES = ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]


def main():
    for m in sys.argv[1:] or MACHINES:
        for name, lines in CASES.items():
            dsk = probe_tmp.tmp(f"fcbcase_{name}_{m}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, diska=dsk, boot=14.0,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=4.0, run_gap=10.0)[0]
            rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr or ""), 40)]
            out = " | ".join(r for r in rows if r.strip() and r.strip() not in ("Ok",))[-260:]
            print(f"{m:28s} {name:14s} [{out}]", flush=True)


if __name__ == "__main__":
    main()
