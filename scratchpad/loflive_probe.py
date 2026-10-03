#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""S10.B design input: LOF and LOC on an OUTPUT channel ACROSS record boundaries.

Earlier work (D-LOF, docs/lof-cf3300-characterization.md §2) measured LOF = 0
on a freshly created file "and still 0 after a PRINT #" -- a few bytes only. S10.B
moves the output path into disk.rom, and main's engine globals stop following a
mode-2 channel, so what LOF/LOC answer after 0, 10, 300 and 600 bytes must be
KNOWN, not inferred (256 B is the CF-3300's record; 512 B our sector).
Screen output only. One summary line: `L lof0 loc0 lof10 loc10 ... #`.
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

PROG = ["NEW", '10 OPEN"LF.TXT"FOR OUTPUT AS#1', "20 DIM L(8)",
        "30 L(0)=LOF(1):L(1)=LOC(1)", '40 PRINT#1,"ABCDEFGH"', "50 L(2)=LOF(1):L(3)=LOC(1)",
        '60 FOR I=1 TO 29:PRINT#1,"ABCDEFGH":NEXT', "70 L(4)=LOF(1):L(5)=LOC(1)",
        '80 FOR I=1 TO 30:PRINT#1,"ABCDEFGH":NEXT', "90 L(6)=LOF(1):L(7)=LOC(1)",
        '100 CLOSE#1:OPEN"LF.TXT"FOR INPUT AS#1:L(8)=LOF(1):CLOSE#1',
        '110 PRINT"L";:FOR I=0 TO 8:PRINT L(I);:NEXT:PRINT"#"', "RUN"]


def main():
    for tag, machine in (("CF-3300", "National_CF-3300"),
                         ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
        dsk = probe_tmp.tmp(f"loflive_{tag}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        raw = omsx_repl.run_cases(machine, [("direct", PROG)], batch=False,
                                  reset=("", "SCREEN 0"), boot=14.0, step=1.5,
                                  run_gap=30.0, diska=dsk)[0] or ""
        scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
        m = re.findall(r"\bL ?((?:-?\d+ ?)+)#", scr)
        print(f"== {tag}: {m[-1] if m else 'NO READING'}")
        print(f"   screen tail: {scr[-200:]}")
    print("   fields: LOF/LOC after 0 B, 10 B, 300 B, 600 B written; then LOF of the file reopened for input")
    return 0


if __name__ == "__main__":
    sys.exit(main())
