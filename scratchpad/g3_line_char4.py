#!/usr/bin/env python3
# G3 LINE error semantics round 4 (VG-8020), using the PROVEN acceptance-probe
# phase-B pattern: 4 auto-numbered lines (10/20/30/40), ON ERROR GOTO 40, handler
# switches to SCREEN0 then prints "E"+ERR; success prints "K". "stored" => auto-run.
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl
REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")

# each: 10 ON ERROR GOTO 40 / 20 <act> / 30 success / 40 handler
CASES = [
    ("ovf_end",     "SCREEN2:LINE(0,0)-(32768,0),15"),
    ("ovf_start",   "SCREEN2:LINE(-32769,0)-(5,5),15"),
    ("ovf_neg",     "SCREEN2:LINE(0,0)-(-32768,0),15"),
    ("scr0",        "SCREEN0:LINE(0,0)-(10,10),15"),
    ("scr1",        "SCREEN1:LINE(0,0)-(10,10),15"),
    ("bf_scr0",     "SCREEN0:LINE(0,0)-(9,9),15,BF"),
    ("badsuffix",   "SCREEN2:LINE(0,0)-(10,10),15,X"),
    ("bare",        "SCREEN2:LINE"),
    ("onepoint",    "SCREEN2:LINE(5,5)"),        # LINE with a single coord, no '-'
    ("huge_offok",  "SCREEN2:LINE(0,0)-(300,300),15"),  # off-screen within int16 -> clip
]
specs, tags = [], []
for label, act in CASES:
    body = ["ON ERROR GOTO 40", act, 'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END']
    specs.append(("stored", body)); tags.append(label)

outs = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW","CLS"))
for label, out in zip(tags, outs):
    txt = " ".join("".join(out).split()) if out else ""
    mk = re.search(r"\bK\b", txt); me = re.search(r"E\s*-?\d+", txt)
    r = ("K (no error)" if mk and not me else (me.group(0).replace(' ','') if me else "?"))
    print(f"  {label:12s} -> {r:14}  raw={txt[:44]!r}")
print("(done)")
