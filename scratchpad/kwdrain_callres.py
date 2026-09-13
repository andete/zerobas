#!/usr/bin/env python3
"""`CALL ZZQ` is blind: an unknown extension and an ABSENT keyword both answer
Syntax error, measured on all three machines (scratchpad/kwdrain_getcall.out).

One angle left, and it is the one D-DONOTHING3 used for SET/IPL/CMD: a RESERVED
word cannot be a variable. `CALL=1` is a Syntax error on a machine that has the
token and an ordinary ASSIGNMENT on one that does not — so the marker prints only
on the stub. That scores RESERVEDNESS rather than behaviour, which is worth
saying out loud, but it is a real differential and it is what separates "the word
is in the table" from "the word parses as a name".
"""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    ("call.res",  'CALL=1:PRINT"[C";CALL;"]"'),
    ("call.ctl",  'ZZQQ=1:PRINT"[C";ZZQQ;"]"'),   # the stub shape: it must PRINT
    ("call.us",   '_ZZQ'),                        # `_` is CALL's abbreviation
]
for name in (sys.argv[1:] or ["zb", "cf3300", "vg8020"]):
    cfg = probe_sides.sides(name)[name]
    kw, tmp = {}, None
    if probe_sides.diska(name, TEST_DSK):
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False); tmp.close()
        shutil.copy(TEST_DSK, tmp.name); kw["diska"] = tmp.name
    specs = [("stored", omsx_repl.as_stored(l)) for _, l in CASES]
    try:
        caps = omsx_repl.run_cases(cfg["machine"], specs, batch=True,
                                   reset=cfg["reset"] + ("NEW", "CLS"),
                                   boot=cfg["boot"], step=4.0, cap_gap=15.0,
                                   timeout=900.0, **kw)
    finally:
        if tmp: os.unlink(tmp.name)
    print("=== %s" % name)
    for (tag, l), cap in zip(CASES, caps):
        print("  %-9s tail=%r" % (tag, omsx_repl.screen_tail(cap, "RUN")))
    sys.stdout.flush()
