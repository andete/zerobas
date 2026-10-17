#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FLDOWN measure-first (2026-10-17): WHERE does the reference keep a FIELD?

Joost ruled the FIELD table moves into disk.rom, and "if reference has a location
inside the non-disk region it uses, we should also use that". So, before any design:
after `FIELD #1,2 AS A$,3 AS B$`, where do A$'s and B$'s descriptors POINT, relative
to the channel's own block (VARPTR(#1)) and to HIMEM; does FIELD cost FRE(0) or
FRE("") anything; does LSET keep the pointer; does a plain `A$=` move it away?
RAM reads only (BASIC PEEK / VARPTR / FRE), on the CF-3300 and on zerobas.
Every variable exists before the first reading (FRE's rule).
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

PROG = ["NEW", "5 CLEAR 400:MAXFILES=1",
        '10 F0=0:F1=0:G0=0:G1=0:VA=0:VB=0:PA=0:PB=0:D=0:H=0:Q=0:A$="":B$=""',
        '20 OPEN"FT.DAT" AS #1 LEN=32',
        '30 D=VARPTR(#1):H=PEEK(&HFC4A)+256*PEEK(&HFC4B):F0=FRE(0):G0=FRE("")',
        "40 FIELD #1,2 AS A$,3 AS B$",
        '50 F1=FRE(0):G1=FRE("")',
        "60 VA=VARPTR(A$):VB=VARPTR(B$):PA=PEEK(VA+1)+256*PEEK(VA+2):PB=PEEK(VB+1)+256*PEEK(VB+2)",
        '70 PRINT"[f";F0-F1;G0-G1;"]":PRINT"[d";H-D;"]"',
        '80 PRINT"[a";PA-D;PEEK(VA);"]":PRINT"[b";PB-D;PEEK(VB);"]"',
        '90 LSET A$="XY":VA=VARPTR(A$):Q=PEEK(VA+1)+256*PEEK(VA+2):PRINT"[l";Q-D;PEEK(Q);"]"',
        '100 A$="Z":VA=VARPTR(A$):Q=PEEK(VA+1)+256*PEEK(VA+2):PRINT"[u";Q-D;"]"',
        '110 CLOSE:KILL"FT.DAT":PRINT"[end]"', "RUN"]
TAGS = ("f", "d", "a", "b", "l", "u", "end")


def main():
    for tag, machine in (("CF-3300", "National_CF-3300"),
                         ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
        dsk = probe_tmp.tmp(f"fieldram_{tag}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        raw = omsx_repl.run_cases(machine, [("direct", PROG)], batch=False,
                                  reset=("", "SCREEN 0:WIDTH 40"), boot=14.0, step=1.5,
                                  run_gap=60.0, diska=dsk)[0] or ""
        flat = re.sub(r"\s+", " ", raw)
        # the typed lines ECHO `[f";F0-F1...` too: a value with a quote is source text,
        # never a reading (a run that dies before its PRINT must read NO READING)
        got = {t: [v for v in re.findall(r"\[" + t + r"([^\]\[]*)\]", flat) if '"' not in v]
               for t in TAGS}
        print(f"== {tag}", flush=True)
        for t in TAGS:
            v = got[t]
            print(f"   [{t}] {v[-1].strip() if v else 'NO READING'}", flush=True)
    print("   [f] FRE(0) and FRE(\"\") spent by FIELD   [d] HIMEM - VARPTR(#1)")
    print("   [a]/[b] descriptor pointer - VARPTR(#1), and its length byte")
    print("   [l] after LSET: pointer - VARPTR(#1), first byte there   [u] after A$=\"Z\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
