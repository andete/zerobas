"""Joost's report (2026-10-16), round 2: which program PREFIX makes `KEY6,"screen0"+CHR$(13)`
raise Out of memory on zerobas Disk BASIC? zerobas DISK vs the CF-3300."""
import sys
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "probes", "lib"))
import omsx_repl

KEYS = ['100 KEY1,"color 15,4,4"+CHR$(13)', '102 KEY2,"auto "', '104 KEY3,"goto "',
        '106 KEY4,"list "', '108 KEY5,"run"+CHR$(13)', '110 KEY6,"screen0"+CHR$(13)',
        '112 KEY7,"load"+CHR$(34)', '114 KEY8,"cont"+CHR$(13)', '116 KEY9,"list."+CHR$(13)',
        '118 KEY10,"files"+CHR$(13)',
        '120 PRINT "[OK";FRE(0);FRE("")"]":END']
PRE = {
    "clrC000": ["10 CLEAR 200,&HC000"],
    "clrD000": ["10 CLEAR 1000,&HD000"],
    "scrn": ["10 SCREEN0:WIDTH40:COLOR15,4,4:KEYOFF"],
    "dim": ["10 DIM A(2800)"],
    "gosub": ["10 GOSUB 100:END", "119 RETURN"],
    "forgs": ["10 FOR I=1 TO 1:GOSUB 100:NEXT:END", "119 RETURN"],
    "onerr": ["10 ON ERROR GOTO 200", "200 PRINT \"[E\";ERR;ERL\"]\":END"],
    "maxf": ["10 MAXFILES=3"],
}
which = sys.argv[1:] or list(PRE)
for name in which:
    prog = ["NEW"] + PRE[name] + KEYS + ["RUN"]
    for m in ("C-BIOS_MSX1_EU_REPACK_DISK", "National_CF-3300"):
        scr = omsx_repl.run_cases(m, [("direct", prog)], batch=False,
                                  reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=15.0)[0]
        r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)] if scr else ["<NO OUTPUT>"]
        keep = [x.strip() for x in r if x.strip().startswith("[") or "rror" in x or "memory" in x
                or " in 1" in x or "space" in x]
        print(f"{name:8} {m:28} {' | '.join(keep) or '<nothing matched>'}", flush=True)
