#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FLDDESC measure-first, round 2 (2026-10-17): the rows where a FIELD TABLE and a
FIELD DESCRIPTOR (the reference's model, scratchpad/fieldram_run.out) would read
differently -- MID$ on a fielded variable, SWAP with one, a copy taken before LSET,
reading after CLOSE and after a re-OPEN. CF-3300 and zerobas, screen output only.
Each value prints between < and >, so a blank-padded field shows its blanks.
FLDDESC_PROG=fresh runs round 3: what a FRESH channel block reads before any LSET
or GET -- on #1 and #2 after MAXFILES, and on #1 after CLEAR re-allocates the blocks.
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

PROG = ["NEW", "5 CLEAR 400:MAXFILES=2",
        '10 A$="":B$="":C$=""',
        '20 OPEN"FD.DAT" AS #1 LEN=8',
        "30 FIELD #1,2 AS A$,3 AS B$",
        '40 LSET A$="XY":RSET B$="Z"',
        '50 PRINT"[r1<";A$;B$;">]":PUT #1,1',
        '60 MID$(A$,1,1)="Q":PRINT"[r2<";A$;">]"',
        '70 GET #1,1:PRINT"[r3<";A$;">]"',
        '80 C$=A$:LSET A$="MN":PRINT"[r4<";C$;A$;">]"',
        '90 SWAP A$,C$:PRINT"[r5<";A$;C$;">]"',
        '100 LSET C$="KL":GET #1,1:PRINT"[r6<";C$;A$;">]"',
        '110 CLOSE #1:PRINT"[r7<";B$;">]"',
        '120 OPEN"FD.DAT" AS #1 LEN=8:PRINT"[r8<";B$;">]"',
        '130 GET #1,1:PRINT"[r9<";B$;">]"',
        '140 CLOSE:KILL"FD.DAT":PRINT"[end]"', "RUN"]
TAGS = ("r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9", "end")
# fresh blocks: the codes of the first two record bytes, on #1 right after MAXFILES=2
# (f1), on #2 (f2), and on #1 again after CLEAR re-allocates the blocks (f3)
FRESH = ["NEW", "5 CLEAR 400:MAXFILES=2", '10 A$="":B$=""',
         '20 OPEN"F1.DAT" AS #1 LEN=8:FIELD #1,2 AS A$:PRINT"[f1";ASC(A$);ASC(MID$(A$,2));"]"',
         '30 OPEN"F2.DAT" AS #2 LEN=8:FIELD #2,2 AS B$:PRINT"[f2";ASC(B$);ASC(MID$(B$,2));"]"',
         '40 LSET A$="QQ":CLOSE:CLEAR 400:MAXFILES=2:A$=""',
         '50 OPEN"F1.DAT" AS #1 LEN=8:FIELD #1,2 AS A$:PRINT"[f3";ASC(A$);ASC(MID$(A$,2));"]"',
         '60 CLOSE:KILL"F1.DAT":KILL"F2.DAT":PRINT"[end]"', "RUN"]
if os.environ.get("FLDDESC_PROG") == "fresh":
    PROG, TAGS = FRESH, ("f1", "f2", "f3", "end")


def main():
    for tag, machine in (("CF-3300", "National_CF-3300"),
                         ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
        dsk = probe_tmp.tmp(f"flddesc_{tag}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        raw = omsx_repl.run_cases(machine, [("direct", PROG)], batch=False,
                                  reset=("", "SCREEN 0:WIDTH 40"), boot=14.0, step=1.5,
                                  run_gap=60.0, diska=dsk)[0] or ""
        flat = raw.replace("\n", "")             # a 40-column row may wrap a value
        print(f"== {tag}", flush=True)
        for t in TAGS:
            # the typed lines ECHO `[r1<";A$...` too: a value with a quote is source
            v = [x for x in re.findall(r"\[" + t + r"([^\]\[]*)\]", flat) if '"' not in x]
            print(f"   [{t}] {v[-1] if v else 'NO READING'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
