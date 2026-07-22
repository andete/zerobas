#!/usr/bin/env python3
# G3 LINE characterization round 3 (VG-8020): error semantics, MODE-SAFE.
# Every case funnels its outcome into a var and PRINTs it in SCREEN0 (the handler
# switches to SCREEN0 before printing), so the name-table capture is always valid.
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl
REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")

# tag T, then the numeric answer. Success prints "T0", error handler prints "T"+ERR.
CASES = [
    ("ovf_end",   ["ON ERROR GOTO 100", "SCREEN2:LINE(0,0)-(32768,0),15",
                   'SCREEN0:PRINT"T0":END', 100, 'SCREEN0:PRINT"T";ERR:END']),
    ("ovf_start", ["ON ERROR GOTO 100", "SCREEN2:LINE(-32769,0)-(5,5),15",
                   'SCREEN0:PRINT"T0":END', 100, 'SCREEN0:PRINT"T";ERR:END']),
    ("ovf_neg32768",["ON ERROR GOTO 100", "SCREEN2:LINE(0,0)-(-32768,0),15",
                   'SCREEN0:PRINT"T0":END', 100, 'SCREEN0:PRINT"T";ERR:END']),
    ("scr0",      ["ON ERROR GOTO 100", "SCREEN0:LINE(0,0)-(10,10),15",
                   'SCREEN0:PRINT"T0":END', 100, 'SCREEN0:PRINT"T";ERR:END']),
    ("scr1",      ["ON ERROR GOTO 100", "SCREEN1:LINE(0,0)-(10,10),15",
                   'SCREEN0:PRINT"T0":END', 100, 'SCREEN0:PRINT"T";ERR:END']),
    ("bf_scr0",   ["ON ERROR GOTO 100", "SCREEN0:LINE(0,0)-(9,9),15,BF",
                   'SCREEN0:PRINT"T0":END', 100, 'SCREEN0:PRINT"T";ERR:END']),
    ("noclose",   ["ON ERROR GOTO 100", "SCREEN2:LINE(0,0)-(10,10),15,X",
                   'SCREEN0:PRINT"T0":END', 100, 'SCREEN0:PRINT"T";ERR:END']),
    ("bare_line", ["ON ERROR GOTO 100", "SCREEN2:LINE",
                   'SCREEN0:PRINT"T0":END', 100, 'SCREEN0:PRINT"T";ERR:END']),
]

def body(c):
    # expand: prefix lines are auto-numbered 10,20,..; the int entry is a line number
    out, ln = [], 10
    for e in c:
        if isinstance(e, int):
            ln = e; continue
        out.append(f"{ln} {e}"); ln += 10
    return out

for label, *rest in [(c[0],)+tuple(c[1]) if False else (c[0], c[1:]) for c in CASES]:
    prog = body(rest[0])
    out = omsx_repl.run_cases(REF, [("direct", prog)], batch=False, reset=("NEW",))[0]
    txt = " ".join("".join(out).split()) if out else ""
    m = re.search(r"T\s*-?\d+", txt)
    print(f"  {label:12s} -> {m.group(0).replace(' ','') if m else '<none>':7}  raw={txt[-50:]!r}")
print("(done)")
