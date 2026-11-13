#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""catalias-acceptance (D-CATALIAS, 2026-11-13): `V$=V$+<computed>` reaches the VG-8020's
string-space capacity -- and the indirect variable slot that does it breaks nothing.

CAPACITY rows: a loop grows V$ until `Out of string space`, then reads ERR, LEN(V$) and
FRE("") -- 100 / 94 / 80 on the VG-8020 for 0 / 12 / 40 bytes held elsewhere (zerobas
read 66 / 62 before). DESIGN rows: CLEAR 201 (the right-hand temporary stays live), V$'s
CONTENT after the error, an array-element left operand, W$=V$+op. SAFETY rows
(scratchpad/catalias_design.md section 5): a GC during the op, aliasing, V$+V$, a new
scalar shifting the arrays mid-expression, DEF FN with V$ as its parameter, an error
inside the expression leaving the variable table intact. Stored programs, the readout
taken after the RUN echo (the fence is also in the echoed source). VG-8020 against zerobas.

Development copies: scratchpad/strspace_probe.py (--limit, --design), scratchpad/
catalias_probe.py. Black-box: BASIC output only.

    python3 -u probes/basic/basic_probe_catalias.py [--gate] [ROW ...]
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

GROW = lambda pre: pre + ['ON ERROR GOTO 50', 'V$="":FOR I=1 TO 99:V$=V$+"AB":NEXT',
                          'PRINT "[M none";LEN(V$);"]":END',
                          'PRINT "[M";ERR;LEN(V$);FRE("");"]":END']
GROWX = lambda pre, op: pre + ['ON ERROR GOTO 50', f'V$="":FOR I=1 TO 99:V$=V$+{op}:NEXT',
                                'PRINT "[M none";LEN(V$);"]":END',
                                'PRINT "[M";ERR;LEN(V$);FRE("");"]":END']
# D-CATALIAS, before building (scratchpad/catalias_design.md §6): the rows the design
# says to measure on the VG-8020 first.
def _grow_custom(pre, body, after):
    return pre + ['ON ERROR GOTO 50', body, 'PRINT "[M none]":END', 'PRINT "[M";ERR;' + after + ';"]":END']
LIMIT_D = {
    # Tk-live (100) or Tk-freed (101)?
    # (99 iterations never ran out on the VG-8020 -- catalias_vg.out: `[M none 99]`)
    "c201": _grow_custom(['CLEAR 201'], 'V$="":FOR I=1 TO 150:V$=V$+CHR$(65):NEXT',
                         'LEN(V$);FRE("")'),
    # V$'s CONTENT intact after the error, not only its length
    "content": _grow_custom(['Q$=""'], 'V$="":FOR I=1 TO 150:V$=V$+CHR$(65+(I MOD 26)):NEXT',
                            'LEN(V$);LEFT$(V$,3);RIGHT$(V$,3);FRE("")'),
    # an ARRAY element as the left operand
    "array": _grow_custom(['DIM A$(2)'], 'A$(1)="":FOR I=1 TO 99:A$(1)=A$(1)+HEX$(I+16):NEXT',
                          'LEN(A$(1));FRE("")'),
    # a DIFFERENT target: W$=V$+op (V$ fixed at 60)
    "wv": _grow_custom(['V$=STRING$(60,"A")'], 'W$="":FOR I=1 TO 99:W$=V$+STRING$(I,"B"):NEXT',
                       'LEN(W$);FRE("")'),
}
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
SAFETY = {
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

ROWS = {}
ROWS.update(LIMIT)
ROWS.update(LIMIT_D)
ROWS.update(SAFETY)
FENCE = {n: "[M" for n in list(LIMIT) + list(LIMIT_D)}


def reading(raw, fence):
    t = " ".join("".join(raw or "").split())
    t = t[t.rfind("RUN"):]
    i = t.rfind(fence)
    return t[i:t.find("]", i) + 1] if i >= 0 else None


def main():
    args = [a for a in sys.argv[1:] if a != "--gate"]
    names = args or list(ROWS)
    got = {}
    for side, mach in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
        raws = omsx_repl.run_cases(mach, [("stored", ROWS[n]) for n in names],
                                   batch=False, run_gap=12.0)
        for n, raw in zip(names, raws):
            got.setdefault(n, {})[side] = reading(raw, FENCE.get(n, "[C"))
    bad = blind = 0
    for n in names:
        a, z = got[n]["VG"], got[n]["ZB"]
        if not a or not z:
            v, blind = "NO-READING", blind + 1
        elif a == z:
            v = "SAME"
        else:
            v, bad = "DIVERGES", bad + 1
        print(f"ROW {n:9} VG={a} ZB={z} {v}", flush=True)
    if blind:
        print("INSTRUMENT FAULT: a side gave no reading")
        return 2
    print(f"{'PASS' if not bad else 'FAIL'}: V$=V$+X capacity and safety against the VG-8020 "
          f"({len(names) - bad}/{len(names)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
