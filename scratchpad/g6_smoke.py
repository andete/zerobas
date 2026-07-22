#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G6 first-run smoke test on the merged zerobas machine (NOT yet a differential).

Purely "does it run at all": the endpoint readouts for a handful of DRAW forms
plus the DEFtype carve's own regression, so a gross failure (hang, wrong tenant,
carve broke DEFINT) shows up before the full differential is written.
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

def rd(tag):
    return (f'PRINT"Q{tag}Q";PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA)')

CASES = [                       # (label, setup line, draw string, expected grpac)
    ("U10",      "", "U10",        "100 90"),
    ("R10",      "", "R10",        "110 100"),
    ("E10",      "", "E10",        "110 90"),
    ("Mabs",     "", "M150,60",    "150 60"),
    ("Mrel",     "", "M+20,+10",   "120 110"),
    ("BU10",     "", "BU10",       "100 90"),
    ("NU10",     "", "NU10",       "100 100"),
    ("S8U10",    "", "S8A0U10",    "100 80"),
    ("A1U10",    "", "S4A1U10",    "90 100"),
    ("chain",    "", "A0S4U10D5",  "100 95"),
    ("lower",    "", "u10",        "100 90"),
    ("semi",     "", "U10;D5",     "100 95"),
    ("eqvar",    "V=10", "U=V;",   "100 90"),
    ("xsub",     'A$="U10"', "XA$;", "100 90"),
    ("xnest",    'A$="XB$;":B$="U10"', "XA$;", "100 90"),
    ("neg",      "", "U-5",        "100 105"),
    ("S3",       "", "S3U10",      "100 93"),
    ("wrap",     "", "S4U32767",   "100 101"),
]
specs = []
for i, (lbl, setup, sdraw, _) in enumerate(CASES):
    head = ":".join(["SCREEN2"] + ([setup] if setup else []))
    specs.append(("stored", [head, f'PSET(100,100):DRAW"A0S4":DRAW"{sdraw}"',
                             f'SCREEN0:{rd(i)}']))
# DEFtype carve regression: the statement still declares types
specs.append(("stored", ['DEFSTR Z:DEFINT A-C', 'Z="hi":A=3.7',
                         'PRINT"Q99Q";A;LEN(Z)']))
outs = omsx_repl.run_cases(ZB, specs, batch=True, reset=("NEW",), capture="screen", cart=None)
bad = 0
for i, (lbl, setup, sdraw, want) in enumerate(CASES):
    txt = " ".join((outs[i] or "").split())
    m = re.search(rf"Q{i}Q([ \d\-]+)", txt)
    got = m.group(1).strip() if m else f"<none> {txt[:50]!r}"
    ok = got == want
    bad += not ok
    print(f"  {'ok ' if ok else 'FAIL'} {lbl:8s} DRAW\"{sdraw}\" -> {got}   (want {want})")
txt = " ".join((outs[-1] or "").split())
m = re.search(r"Q99Q([ \d\-]+)", txt)
got = m.group(1).strip() if m else f"<none> {txt[:60]!r}"
ok = got.split() == ["3", "2"]   # A=3.7 -> 3: our float->int TRUNCATES (documented
                                 # deviation, spec-basic-float-core §10); what matters
                                 # here is that the carved DEFINT/DEFSTR took effect
bad += not ok
print(f"  {'ok ' if ok else 'FAIL'} DEFtype  DEFSTR/DEFINT -> {got}   (want '3 2')")
print(f"\n{len(CASES)+1-bad}/{len(CASES)+1} passed")
