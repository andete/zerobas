#!/usr/bin/env python3
"""D-FNALIAS RAM (Joost 2026-11-07: "measure what reference does? we try to match RAM?"):
what free memory a DEF FN call with arguments costs, on the VG-8020, the CF-3300 and
zerobas. FRE(0) read INSIDE the body against FRE(0) read just before the call, for
N = 0..9 numeric (single, integer, double) and string actuals; and a nested call (one
FN calling another) for the per-level cost. BASIC only.

    python3 -u scratchpad/fnram_probe.py [case...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides                               # noqa: E402

LET = "ABCDEFGHI"


def fn(n, sfx, actual):
    """DEF FNA with n formals of suffix sfx whose body is FRE(0) (+ 0*formals so all are
    used); the call passes `actual` n times."""
    forms = ",".join(f"{LET[i]}{sfx}" for i in range(n))
    if sfx == "$":
        use = "+".join(f"0*LEN({LET[i]}$)" for i in range(n)) or "0"
    else:
        use = "+".join(f"0*{LET[i]}{sfx}" for i in range(n)) or "0"
    head = f"DEF FNA({forms})" if n else "DEF FNA"
    call = f"FNA({','.join([actual] * n)})" if n else "FNA"
    return f"20 {head}=FRE(0)+{use}", call


CASES = []
for sfx, actual, tag in (("", "1", "s"), ("%", "1", "i"), ("#", "1", "d"), ("$", 'Z$', "z")):
    for n in (0, 1, 2, 5, 9):
        if n == 0 and tag != "s":
            continue
        CASES.append((f"{tag}{n}", sfx, actual, n))


def prog(tag, sfx, actual, n):
    d, call = fn(n, sfx, actual)
    return ["10 CLEAR 300:Z$=\"QQ\"", d,
            f"30 F0=FRE(0):F1={call}",
            f'40 PRINT CHR$(91);"{tag}";F0;F1;F0-F1;CHR$(93)', "RUN"]


def prog_peak(tag, sfx, actual, n):
    """FRE(0) as the LAST actual, after n parked actuals of suffix sfx: the peak."""
    forms = ",".join([f"{LET[i]}{sfx}" for i in range(n)] + ["J"])
    call = "FNA(" + ",".join([actual] * n + ["FRE(0)"]) + ")"
    return ["10 CLEAR 300:Z$=\"QQ\"", f"20 DEF FNA({forms})=J",
            f"30 F0=FRE(0):F1={call}",
            f'40 PRINT CHR$(91);"{tag}";F0;F1;F0-F1;CHR$(93)', "RUN"]


PEAK = [(f"p{t}{n}", prog_peak(f"p{t}{n}", s, a, n))
        for s, a, t in (("", "1", "s"), ("#", "1", "d"), ("$", "Z$", "z"), ("$", '"AB"', "l"))
        for n in (0, 1, 2, 5, 8)]

NEST = [("nest1", ['10 CLEAR 300', '20 DEF FNB(X)=FRE(0)+0*X', '25 DEF FNA(X)=FNB(X)+0*X',
                   '30 F0=FRE(0):F1=FNB(1):F2=FNA(1)',
                   '40 PRINT CHR$(91);"nest1";F0;F1;F2;F0-F1;F1-F2;CHR$(93)', "RUN"])]


def fence(tag, cap):
    c = cap or ""; k = len(c)
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0:
            return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]:
            return " ".join(c[i + len(tag) + 1:j].split())
        k = i


sides = ("vg8020", "cf3300", "zb")
cfg = probe_sides.sides(*sides)
only = sys.argv[1:]
rows = [(t, prog(t, s, a, n)) for t, s, a, n in CASES] + NEST + PEAK
print("case   F0(before) F1(in body) F0-F1 [nest: F0 F1 F2 F0-F1 F1-F2]")
for tag, p in rows:
    if only and tag not in only:
        continue
    got = []
    for side in sides:
        cap = omsx_repl.run_cases(cfg[side]["machine"], [(tag, p)], batch=False,
                                  boot=cfg[side]["boot"], reset=cfg[side]["reset"], run_gap=6.0)[0]
        got.append(fence(tag, cap))
    print(f"{tag:6} vg8020=[{got[0]}]  cf3300=[{got[1]}]  zb=[{got[2]}]", flush=True)
print(__import__("probe_refcache").summary())
