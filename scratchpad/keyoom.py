"""Joost's report (2026-10-16): `110 KEY6,"screen0"+CHR$(13)` -> Out of memory in 110 on zerobas
Disk BASIC. Which programs reproduce it, and what do the references answer?"""
import os, sys
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "probes", "lib"))
import omsx_repl

KEYS = ['100 KEY1,"color 15,4,4"+CHR$(13)', '102 KEY2,"auto "', '104 KEY3,"goto "',
        '106 KEY4,"list "', '108 KEY5,"run"+CHR$(13)', '110 KEY6,"screen0"+CHR$(13)',
        '120 PRINT "[OK";FRE(0);FRE("")"]"']
P = {
    "direct": ['KEY6,"screen0"+CHR$(13):PRINT "[OK";FRE(0);FRE("")"]"'],
    "keys": ["NEW"] + KEYS + ["RUN"],
    "cl200": ["NEW", "10 CLEAR 200"] + KEYS + ["RUN"],
    "cl0": ["NEW", "10 CLEAR 0"] + KEYS + ["RUN"],
    "fre": ['PRINT "[F";FRE(0);FRE("")"]"'],
}
which = sys.argv[1:] or list(P)
for name in which:
    for m in ("C-BIOS_MSX1_EU_REPACK_DISK", "National_CF-3300", "C-BIOS_MSX1_EU_REPACK_NODISK", "Philips_VG_8020"):
        scr = omsx_repl.run_cases(m, [("direct", P[name])], batch=False,
                                  reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=15.0)[0]
        r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)] if scr else ["<NO OUTPUT>"]
        keep = [x.strip() for x in r if x.strip().startswith("[") or "rror" in x or "memory" in x
                or "in 1" in x]
        print(f"{name:7} {m:30} {' | '.join(keep) or '<nothing matched>'}", flush=True)
