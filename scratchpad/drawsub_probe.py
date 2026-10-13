#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""RAM order step (2), the design question: WHAT may follow `=` and `X` in a
DRAW string on the VG-8020?

zerobas copies every DRAW string into a 256 B buffer because its co-routine
resolves `=expr;` / `X expr$;` through the resident's eval between round
trips, and an eval can allocate (temporaries, a GC) and so move a string body
it was reading in place. If the reference accepts only VARIABLES there,
nothing allocates during a DRAW and the string can be read in place, as the
reference does (drawbuf_probe.out: no buffer) -- the 256 B buffer has no job.

Each case: a program sets variables, enters SCREEN 2, runs one DRAW under ON
ERROR, returns to SCREEN 0 and prints [OK] or [E n].

Prediction (2026-10-13): VG-8020 -- a plain variable and an array element are
accepted, every expression and every constant raises an error; zerobas accepts
the expressions (a superset).
"""
import os, sys
os.environ.setdefault("ZEROBAS_REFCACHE", "0")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
CASES = [
    ("var", "R=A;"),
    ("arr", "R=B(1);"),
    ("expr", "R=A+1;"),
    ("paren", "R=(A);"),
    ("const", "R=5;"),
    ("fn", "R=ABS(A);"),
    ("newvar", "R=Q;"),
    ("xvar", "XA$;"),
    ("xarr", "XC$(1);"),
    ("xexpr", "XA$+D$;"),
    ("xlit", 'X"R2";'),
    ("xfn", "XLEFT$(A$,2);"),
    ("empty", "R=;"),
    ("neg", "R=-A;"),
    ("lower", "R=a;"),
    ("xempty", "X;"),
]


def prog(sub):
    s = sub.replace('"', '"+CHR$(34)+"')
    return ["NEW", "10 ON ERROR GOTO 100",
            '20 A=5:DIM B(2):B(1)=3:A$="R2":D$="D2":DIM C$(2):C$(1)="U2"',
            f'30 SCREEN 2:DRAW "BM50,50{s}":SCREEN 0:PRINT"[OK]":END',
            '100 SCREEN 0:PRINT"[E"ERR"]":END', "RUN"]


def main():
    width = max(len(n) for n, _ in CASES)
    for m in MACHINES:
        print(f"=== {m}", flush=True)
        for name, sub in CASES:
            raw = omsx_repl.run_cases(m, [("direct", prog(sub))], batch=False,
                                      reset=("", "SCREEN 0"), run_gap=8.0)[0]
            span = omsx_repl.result_span(raw) if raw else None
            print(f"   {name:{width}s} {sub:16s} -> {('[' + span + ']') if span else 'NO READING'}",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
