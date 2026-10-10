# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-NGRAM 2026-10-10: a witness for str_set_key's Out-of-memory branch, which
array-acceptance never reaches (its OOM rows assign LITERALS, stored by
reference -- scratchpad/carve2_knife.out). A non-literal RHS (`CHR$(65)`) takes
str_set_key's scalar allocation, and with HIMEM pulled down the run of A$..Z$
must end in Out of memory (7), trapped, with the variable count reached.

  oom   DIM D#(FRE(0)/8-22) eats the room, then A$..Z$ = CHR$(65) under ON
        ERROR; prints ERR and N (a typed CLEAR 10,&H8200 was ignored here: HIMEM stayed $E000)

Usage: sskoom_probe.py [machine ...]  (default: VG-8020 and zerobas NODISK)
Clean-room: typed BASIC in, the text screen out.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

L1 = "20 N=0:" + ":".join(f"{c}$=CHR$(65):N=N+1" for c in "ABCDEFGHIJKLM")
L2 = "30 " + ":".join(f"{c}$=CHR$(65):N=N+1" for c in "NOPQRSTUVWXYZ")
LINES = ["NEW", "10 ON ERROR GOTO 90", "15 DIM D#(FRE(0)/8-22)", L1, L2,
         '40 PRINT "NO OOM";N:END', '90 PRINT "ERR";ERR;"N";N:END', "RUN"]


def rows(scr):
    if scr is None:
        return "<NO CAPTURE>"
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "RUN" in r:
        r = r[r.index("RUN") + 1:]
    return " | ".join(x for x in r if x and x.strip() not in ("Ok", "ZB"))


for m in sys.argv[1:] or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]:
    scr = omsx_repl.run_cases(m, [("direct", LINES)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0)[0]
    print(f"{m:30s} [{rows(scr)}]", flush=True)
