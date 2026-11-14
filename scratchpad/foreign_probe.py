#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CALLSTMT inventory (Joost 2026-11-14, "ideally yes": another MSX BASIC driving OUR
disk ROM is a target). Every Disk BASIC statement / function under the CF-3300's OWN
BASIC, with its own disk ROM (National_CF-3300) and with ours
(National_CF-3300_ZEROBASDISK), each row on a fresh copy of disk/test720.dsk. Typed keys
in, the text screen out (omsx_repl, as disk_probe_callsystem.py). Rows: SAME / DIVERGES.

    python3 -u scratchpad/foreign_probe.py [ROW ...]
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl   # noqa: E402
import probe_tmp   # noqa: E402

ROWS = {
    "files":   ['FILES'],
    "dskf":    ['PRINT DSKF(0)'],
    "save":    ['10 PRINT "HI"', 'SAVE "P.BAS"', 'NEW', 'LOAD "P.BAS"', 'LIST'],
    "savea":   ['10 PRINT "HI"', 'SAVE "PA.BAS",A', 'NEW', 'LOAD "PA.BAS"', 'LIST'],
    "run":     ['10 PRINT "RAN"', 'SAVE "R.BAS"', 'NEW', 'RUN "R.BAS"'],
    "merge":   ['10 PRINT "A"', 'SAVE "M.BAS",A', 'NEW', '20 PRINT "B"', 'MERGE "M.BAS"', 'LIST'],
    "openw":   ['OPEN "T.TXT" FOR OUTPUT AS 1', 'PRINT #1,"LINE"', 'CLOSE', 'PRINT "[OK]"'],
    "openr":   ['OPEN "T.TXT" FOR OUTPUT AS 1:PRINT #1,"LINE":CLOSE',
                'OPEN "T.TXT" FOR INPUT AS 1:LINE INPUT #1,A$:PRINT EOF(1);LOF(1);"[";A$;"]":CLOSE'],
    "append":  ['OPEN "T.TXT" FOR OUTPUT AS 1:PRINT #1,"A":CLOSE',
                'OPEN "T.TXT" FOR APPEND AS 1:PRINT #1,"B":CLOSE',
                'OPEN "T.TXT" FOR INPUT AS 1:INPUT #1,A$,B$:PRINT A$;B$:CLOSE'],
    "random":  ['OPEN "R.DAT" AS 1 LEN=16:FIELD 1,16 AS F$:LSET F$="REC":PUT 1,2:CLOSE',
                'OPEN "R.DAT" AS 1 LEN=16:FIELD 1,16 AS F$:GET 1,2:PRINT "[";F$;"]";LOC(1):CLOSE'],
    "kill":    ['OPEN "K.TXT" FOR OUTPUT AS 1:CLOSE', 'KILL "K.TXT"', 'PRINT "[OK]"'],
    "name":    ['OPEN "N.TXT" FOR OUTPUT AS 1:CLOSE', 'NAME "N.TXT" AS "M.TXT"', 'FILES "?.TXT"'],
    "copy":    ['OPEN "C.TXT" FOR OUTPUT AS 1:PRINT #1,"X":CLOSE', 'COPY "C.TXT" TO "D.TXT"',
                'FILES "?.TXT"'],
    "bsave":   ['BSAVE "B.BIN",&HC000,&HC00F', 'BLOAD "B.BIN"', 'PRINT "[OK]"'],
    "maxfiles": ['MAXFILES=3', 'PRINT "[OK]"'],
    "dski":    ['A$=DSKI$(0,0):PRINT LEN(A$);ASC(A$)'],
    "lfiles":  ['LFILES', 'PRINT "[OK]"'],
    "notfound": ['LOAD "NOSUCH.BAS"'],
}


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)]
    return " | ".join(x for x in r if x and x.strip() not in ("Ok", "ZB"))


def main():
    names = sys.argv[1:] or list(ROWS)
    bad = []
    for name in names:
        got = {}
        for side, m in (("CF", "National_CF-3300"), ("ZD", "National_CF-3300_ZEROBASDISK")):
            dsk = probe_tmp.tmp(f"foreign_{name}_{side}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            try:
                got[side] = rows(omsx_repl.run_cases(m, [("direct", ROWS[name])], batch=False,
                                                     diska=dsk, boot=14.0,
                                                     reset=("", "SCREEN 0:WIDTH 40"),
                                                     step=5.0, run_gap=20.0)[0])
            except SystemExit as e:
                got[side] = "<APPARATUS: " + str(e).splitlines()[0][:70] + ">"
        v = "SAME" if got["CF"] == got["ZD"] else "DIVERGES"
        if v != "SAME":
            bad.append(name)
        print(f"ROW {name} {v}\n   CF=[{got['CF']}]\n   ZD=[{got['ZD']}]", flush=True)
    print(f"\n{len(names) - len(bad)}/{len(names)} SAME; diverging: {' '.join(bad) or '-'}")


if __name__ == "__main__":
    main()
