#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CATALIAS's safety rows (scratchpad/catalias_design.md §5): what the indirect variable
slot must not break -- a GC during the op, aliasing, V$+V$, a new scalar shifting the
arrays mid-expression, DEF FN with V$ as its parameter, an error inside the expression
leaving the variable table intact. Stored programs; VG-8020 against zerobas.

    python3 -u scratchpad/catalias_probe.py [ROW ...]
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CASES = {
    "gc_op":   ['ON ERROR GOTO 30:CLEAR 300:V$=STRING$(60,"A"):W$=STRING$(60,"B"):W$="":V$=V$+STRING$(70,"C")',
                'PRINT "[C";LEN(V$);LEFT$(V$,1);RIGHT$(V$,1);FRE("");"]":END',
                'PRINT "[C E";ERR;LEN(V$);"]":END'],
    "alias":   ['V$="ABC":W$=V$+"X":MID$(W$,1,1)="Z"', 'PRINT "[C";V$;" ";W$;"]"'],
    "vv":      ['V$="AB":V$=V$+V$', 'PRINT "[C";V$;"]"'],
    "vnest":   ['V$="AB":V$=V$+(V$+"C")', 'PRINT "[C";V$;"]"'],
    "w_vv":    ['V$="AB":W$=V$+V$+V$', 'PRINT "[C";V$;" ";W$;"]"'],
    "ary_new": ['DIM A$(2):A$(1)=STRING$(60,"A"):A$(1)=A$(1)+STRING$(3,"N")+N$', 'PRINT "[C";LEN(A$(1));RIGHT$(A$(1),3);"]"'],
    "ary_gc":  ['ON ERROR GOTO 30:CLEAR 300:DIM A$(2):A$(1)=STRING$(60,"A"):W$=STRING$(60,"B"):W$="":A$(1)=A$(1)+STRING$(70,"C")',
                'PRINT "[C";LEN(A$(1));LEFT$(A$(1),1);RIGHT$(A$(1),1);FRE("");"]":END',
                'PRINT "[C E";ERR;LEN(A$(1));"]":END'],
    "fn_par":  ['DEF FNA$(V$)=V$+"Z":V$="Q":W$=V$+FNA$("P")', 'PRINT "[C";V$;" ";W$;"]"'],
    "fn_cat":  ['DEF FNA$(X$)=X$+"Z":V$="Q":V$=V$+FNA$("P")', 'PRINT "[C";V$;"]"'],
    "oom_mid": ['CLEAR 200:ON ERROR GOTO 30:Q$="KEEP":V$=STRING$(150,"A")',
                'X$=MID$(V$+STRING$(100,"B"),2):PRINT "[N]":END',
                'PRINT "[C";ERR;Q$;LEN(V$);LEFT$(V$,1);"]":END'],
    "empty":   ['V$="":V$=V$+"":W$=V$+"X"', 'PRINT "[C";LEN(V$);W$;"]"'],
    "len255":  ['CLEAR 600:ON ERROR GOTO 30:V$=STRING$(200,"A"):V$=V$+STRING$(60,"B")', 'PRINT "[N]":END',
                'PRINT "[C";ERR;LEN(V$);"]":END'],
}


def main():
    names = sys.argv[1:] or list(CASES)
    res = {}
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
        raws = omsx_repl.run_cases(mach, [("stored", CASES[n]) for n in names],
                                   batch=False, run_gap=12.0)
        for n, raw in zip(names, raws):
            t = " ".join("".join(raw or "").split())
            t = t[t.rfind("RUN"):]          # the fence is also in the echoed source
            i = t.rfind("[C")
            res.setdefault(n, {})[mach[:2]] = t[i:t.find("]", i) + 1] if i >= 0 else "<NO [C> " + t[-40:]
    for n in names:
        a, b = res[n]["Ph"], res[n]["C-"]
        print(f"ROW {n:8} VG={a} ZB={b} {'SAME' if a == b else 'DIVERGES'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
