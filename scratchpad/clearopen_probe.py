#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""S10.B design input 3: what does `CLEAR n` do to a channel open FOR OUTPUT?

S10.B caches each output channel's 265 B FCB block address on the disk side.
The block table's base is derived from the string pool's size, so a `CLEAR n`
that leaves the channel open would move the block under the cache. Whether the
reference CLOSES files on CLEAR decides the design, so it is measured first.

After `PRINT#1` of 10 bytes and `CLEAR 500` (and `CLEAR 200,&HE000` in case
two), a second `PRINT#1` is tried under ON ERROR; then the file is reopened for
input and its LOF read. One summary line per case: `W` (the write worked) or
`E <err>`, then `L <lof>`. The rej* cases are CLEARs the reference REJECTS
(ERR 5 / 7): does a rejected CLEAR still close the file?
Screen output only.
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402


def prog(clear):
    # the handler is armed BEFORE the CLEAR too: a REJECTED CLEAR raises with
    # it still alive (D-CLRTRAP), an accepted one kills it and line 40 re-arms
    return ["NEW", '10 OPEN"CL.TXT"FOR OUTPUT AS#1', '20 PRINT#1,"ABCDEFGH"',
            "25 ON ERROR GOTO 100", f"30 {clear}", "40 ON ERROR GOTO 100",
            '50 PRINT#1,"XYZ":PRINT"W";',
            "60 CLOSE#1", '70 OPEN"CL.TXT"FOR INPUT AS#1:PRINT"L";LOF(1);"#":CLOSE', "80 END",
            '100 PRINT"E";ERR;:RESUME NEXT', "RUN"]


CASES = {"clear500": "CLEAR 500", "clearhimem": "CLEAR 200,&HE000", "control": "REM",
         "bare": "CLEAR", "rejneg": "CLEAR -1", "rejoom": "CLEAR 30000",
         "rejhim": "CLEAR 200,&H100"}


def main():
    for case in (sys.argv[1:] or CASES):
        clear = CASES[case]
        for tag, machine in (("CF-3300", "National_CF-3300"),
                             ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
            dsk = probe_tmp.tmp(f"clearopen_{tag}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            raw = omsx_repl.run_cases(machine, [("direct", prog(clear))], batch=False,
                                      reset=("", "SCREEN 0"), boot=14.0, step=1.5,
                                      run_gap=30.0, diska=dsk)[0] or ""
            scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
            m = re.findall(r"((?:[WE][^L#]*)?L ?-?\d+ ?#)", scr)
            print(f"== {case:10} {tag:8}: {m[-1] if m else 'NO READING'}", flush=True)
            print(f"   screen tail: {scr[-160:]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
