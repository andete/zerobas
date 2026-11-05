#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-INPQUOTE / D-INPQUOTE2 (gate: inpquote-acceptance): a STRING INPUT # field --
its blanks, its quotes, and what it leaves for the next read.

Each row writes a file with PRINT #1,<w>:PRINT #1,"NX", then reads it back with
INPUT #1,A$ and LINE INPUT #1,R$, and prints [A$ with blanks as _ and quotes as
# | LEN(A$) | R$ ERR]. Measured on the CF-3300 (scratchpad/inpquote_run.out):
leading blanks are shed, trailing and embedded ones kept; a `"` as the first
byte opens a quoted field, inside which commas, CR and LF are data; after the
closing quote ONE comma, or ONE CR with its LF, goes with the field and anything
else is the NEXT read's (`"AB"CD` leaves CD; an unclosed quote reads to the end
of the file, and the LINE INPUT after it is 55). zerobas's reader could not peek
and dropped what followed the quote until 2026-11-05 (disk.rom din_str).

A fresh copy of disk/test720.dsk per case and side. Exit 0 all agree, 1 a
divergence, 2 the CF-3300 gave no reading on a row.
Clean-room: typed BASIC in, the text screen out. CF-3300 vs zerobas DISK.
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

Q = 'CHR$(34)'
SHOW = ('B$="":FOR I=1 TO LEN(A$):C$=MID$(A$,I,1):IF C$=" " THEN C$="_" ELSE IF C$=CHR$(34) THEN C$="#"',
        'B$=B$+C$:NEXT')
FILE = [("num", '5'), ("lead", '"  AB"'), ("trail", '"AB  "'), ("embed", '"A B"'),
        ("both", '"  AB  "'), ("quoted", Q + '+"  AB  "+' + Q), ("comma", '"  AB  ,CD"'),
        ("empty", '""'), ("qcomma", Q + '+"A,B"+' + Q),
        ("qjunk", Q + '+"AB"+' + Q + '+"CD"'), ("qjunkc", Q + '+"AB"+' + Q + '+"CD,EF"'),
        ("qopen", Q + '+"AB,CD"'), ("qmid", '"A"+' + Q + '+"B"+' + Q),
        ("qlead", '"  "+' + Q + '+"AB"+' + Q)]
SIDES = (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK"))


def program(w):
    return ["NEW", "10 ON ERROR GOTO 90",
            f'20 OPEN "S.TXT" FOR OUTPUT AS #1:PRINT #1,{w}:PRINT #1,"NX":CLOSE',
            '30 OPEN "S.TXT" FOR INPUT AS #1:INPUT #1,A$:LINE INPUT #1,R$:CLOSE',
            f"40 {SHOW[0]}", f"41 {SHOW[1]}",
            '60 PRINT CHR$(91);B$;"|";LEN(A$);"|";R$;E;CHR$(93):END',
            "90 E=ERR:RESUME 60", "RUN"]


def main():
    only = sys.argv[1:]
    bad, blind = [], []
    for name, w in FILE:
        if only and name not in only:
            continue
        got = {}
        for side, m in SIDES:
            cf = side == "CF"
            dsk = probe_tmp.tmp(f"inpquote_{name}_{side}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            raw = omsx_repl.run_cases(m, [("direct", program(w))], batch=False,
                                      reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                      boot=14.0 if cf else 8.0, capture="screen", step=4.0,
                                      diska=dsk)[0] or ""
            r = re.findall(r"\[[^\]\"]*\]", raw)
            got[side] = r[-1] if r else None
        if got["CF"] is None:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["CF"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name:7s} CF={got['CF']} ZB={got['ZB']} {verdict}", flush=True)
    print(__import__("probe_refcache").summary())
    if blind:
        print(f"INSTRUMENT FAULT: the CF-3300 gave no reading on {', '.join(blind)}")
        return 2
    print(f"{'PASS' if not bad else 'FAIL'}: INPUT # string fields ({len(bad)} diverge)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
