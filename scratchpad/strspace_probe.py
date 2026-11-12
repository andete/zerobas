#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Found by playq_probe.py (2026-11-12): zerobas stopped with `Out of string space in
40` building a 64-character string by 32 concatenations under the default CLEAR 200;
the VG-8020 ran it. Isolate: with and without a PLAY first, and FRE("") along the way.

    python3 -u scratchpad/strspace_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

LOOP = ['V$="":FOR I=0 TO 31:V$=V$+RIGHT$("0"+HEX$(PEEK(&HF975+I)),2):NEXT',
        'PRINT "[S";LEN(V$);FRE("");"]"']
VL = lambda n: [f'V$="":FOR I=1 TO {n}:V$=V$+RIGHT$("0"+HEX$(I),2):NEXT',
                'PRINT "[S";LEN(V$);FRE("");"]"']
QC = ['Q$="":FOR I=0 TO 5:Q$=Q$+RIGHT$("0"+HEX$(I),2):NEXT']
MATRIX = {
    "q1alloc_v32": ['Q$=STRING$(12,65)'] + VL(32),
    "qcat_v8":     QC + VL(8),
    "qcat_v16":    QC + VL(16),
    "qcat_v32":    QC + VL(32),
    "qcat_fre_v32": QC + ['R=FRE("")'] + VL(32),
}
# how far V$ grows (2 a step) before ERR 14, with / without a live 12-byte Q$
GROW = lambda pre: pre + ['ON ERROR GOTO 50', 'V$="":FOR I=1 TO 99:V$=V$+"AB":NEXT',
                          'PRINT "[M none";LEN(V$);"]":END',
                          'PRINT "[M";ERR;LEN(V$);FRE("");"]":END']
GROWX = lambda pre, op: pre + ['ON ERROR GOTO 50', f'V$="":FOR I=1 TO 99:V$=V$+{op}:NEXT',
                                'PRINT "[M none";LEN(V$);"]":END',
                                'PRINT "[M";ERR;LEN(V$);FRE("");"]":END']
LIMIT = {
    "rh_noq":  GROWX(['Q$=""'], 'RIGHT$("0"+HEX$(I),2)'),
    "rh_q12":  GROWX(['Q$=STRING$(12,65)'], 'RIGHT$("0"+HEX$(I),2)'),
    "hex_q12": GROWX(['Q$=STRING$(12,65)'], 'HEX$(I+16)'),
    "cat_q12": GROWX(['Q$=STRING$(12,65)'], '("A"+"B")'),
    "rt_q12":  GROWX(['Q$=STRING$(12,65)'], 'RIGHT$("XAB",2)'),
    "grow_noq": GROW(['Q$=""']),
    "grow_q12": GROW(['Q$=STRING$(12,65)']),
    "grow_q40": GROW(['Q$=STRING$(40,65)']),
}
CASES = {
    "noplay": ['PRINT "[F";FRE("");"]"'] + LOOP,
    "play":   ['PLAY "C":PRINT "[F";FRE("");"]"'] + LOOP,
    # the failing program's shape: Q$ by 6 concatenations, THEN V$ by 32
    "qthenv": ['Q$="":FOR I=0 TO 5:Q$=Q$+RIGHT$("0"+HEX$(PEEK(&HF959+I)),2):NEXT'] + LOOP,
    "qthenv_play": ['PLAY "C":T=TIME', 'IF TIME-T<120 THEN 20',
                    'Q$="":FOR I=0 TO 5:Q$=Q$+RIGHT$("0"+HEX$(PEEK(&HF959+I)),2):NEXT'] + LOOP,
    "simple": ['PRINT "[F";FRE("");"]"', 'V$="":FOR I=0 TO 31:V$=V$+"AB":NEXT',
               'PRINT "[S";LEN(V$);FRE("");"]"'],
}


def main():
    global CASES
    if "--matrix" in sys.argv:
        CASES = MATRIX
    if "--limit" in sys.argv:
        CASES = LIMIT
    names = list(CASES)
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
        raws = omsx_repl.run_cases(mach, [("stored", CASES[n]) for n in names],
                                   batch=False, run_gap=5.0)
        for n, raw in zip(names, raws):
            txt = " ".join("".join(raw or "").split())
            i = txt.rfind("RUN")
            print(f"{mach[:10]:10} {n:7} {txt[i:i + 90] if i >= 0 else txt[-90:]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
