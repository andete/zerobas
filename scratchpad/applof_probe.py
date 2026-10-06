#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""S10.B increment 2 design input: LOF and LOC on an APPEND channel.

APPEND will move onto disk.rom's 256 B record writer, which resumes at the last
WHOLE record -- so what LOF/LOC answer right after OPEN ... FOR APPEND, and after
10 and 300 appended bytes, must be KNOWN. Two starting files, written FOR OUTPUT:
`OLD` (6 B with CR LF and the Ctrl-Z) and 255 x `A` (256 B, the Ctrl-Z the
256th -- a whole record). Then the file's size reopened for input.
Screen output only. One summary line per start: `L lof0 loc0 lof10 loc10 lof300 loc300 size #`.
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

START = {"6B": 'PRINT#1,"OLD"', "256B": 'PRINT#1,STRING$(255,"A");'}


def prog(first):
    return ["NEW", "5 CLEAR 400", '10 OPEN"AP.TXT"FOR OUTPUT AS#1', f"20 {first}", "30 CLOSE#1", "40 DIM L(6)",
            '50 OPEN"AP.TXT"FOR APPEND AS#1:L(0)=LOF(1):L(1)=LOC(1)',
            '60 PRINT#1,"ABCDEFGH":L(2)=LOF(1):L(3)=LOC(1)',
            '70 FOR I=1 TO 29:PRINT#1,"ABCDEFGH":NEXT:L(4)=LOF(1):L(5)=LOC(1)',
            '80 CLOSE#1:OPEN"AP.TXT"FOR INPUT AS#1:L(6)=LOF(1):CLOSE#1',
            '90 PRINT:PRINT"L";:FOR I=0 TO 6:PRINT MID$(STR$(L(I)),2);",";:NEXT:PRINT"#"', "RUN"]


def main():
    for start, first in START.items():
        for tag, machine in (("CF-3300", "National_CF-3300"),
                             ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
            dsk = probe_tmp.tmp(f"applof_{tag}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            raw = omsx_repl.run_cases(machine, [("direct", prog(first))], batch=False,
                                      reset=("", "SCREEN 0"), boot=14.0, step=1.5,
                                      run_gap=60.0, diska=dsk)[0] or ""
            scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
            m = re.findall(r"L(\d+(?:,\d+){6},)#", scr.replace(" ", ""))
            print(f"== {start:5} {tag:8}: {m[-1] if m else 'NO READING'}", flush=True)
    print("   fields: LOF,LOC after OPEN APPEND; after 10 B; after 300 B; size reopened")
    return 0


if __name__ == "__main__":
    sys.exit(main())
