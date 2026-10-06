#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DISKERRS, the channel-direction shape: PRINT# / INPUT# / LINE INPUT# on a
channel opened the other way (or RANDOM) -- which error, and trappable?

Each case: a trap prints `e<ERR>@<ERL>`; the program then prints `R<..>#`.
Fresh test720 copy per case, on the CF-3300 and on ours.

    python3 -u scratchpad/chdir_probe.py
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_tmp                        # noqa: E402

CASES = {
    "print_in":   ['OPEN"P1.TXT"FOR OUTPUT AS#1:CLOSE#1', 'OPEN"P1.TXT"FOR INPUT AS#1', 'PRINT#1,"A"'],
    "print_rnd":  ['OPEN"P2.DAT"AS#1', 'PRINT#1,"A"'],
    "input_out":  ['OPEN"P3.TXT"FOR OUTPUT AS#1', 'INPUT#1,A$'],
    "linein_out": ['OPEN"P4.TXT"FOR OUTPUT AS#1', 'LINE INPUT#1,A$'],
    "input_rnd":  ['OPEN"P5.DAT"AS#1', 'INPUT#1,A$'],
    "input_app":  ['OPEN"P6.TXT"FOR OUTPUT AS#1:CLOSE#1', 'OPEN"P6.TXT"FOR APPEND AS#1', 'INPUT#1,A$'],
}


def prog(body):
    lines = ["NEW", "5 ON ERROR GOTO 900"]
    lines += [f"{10 + 10 * i} {s}" for i, s in enumerate(body)]
    lines += ['800 PRINT"R<";E$;">#":END', '900 E$=E$+"e"+MID$(STR$(ERR),2)+"@"+MID$(STR$(ERL),2):RESUME 800', "RUN"]
    return lines


def main():
    for case, body in CASES.items():
        for tag, machine in (("CF-3300", "National_CF-3300"), ("OURS", "C-BIOS_MSX1_EU_REPACK_DISK")):
            dsk = probe_tmp.tmp(f"chdir_{case}_{tag}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            raw = omsx_repl.run_cases(machine, [("d", prog(body))], batch=False, reset=("", "SCREEN 0"),
                                      boot=14.0, step=3.0, run_gap=20.0, diska=dsk)[0] or ""
            scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
            m = re.findall(r"R<([^>#]*)>#", scr)
            print(f"== {case:10} {tag:8} {m[-1] if m else 'NO READING: ' + scr[-120:]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
