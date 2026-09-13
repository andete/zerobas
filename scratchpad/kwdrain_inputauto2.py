#!/usr/bin/env python3
"""Round 2. Round 1 proved AUTO's blast radius by sacrificing two rows to it —
the harness flagged both as MIS-DELIVERED and then REFUSED on the CF-3300 rather
than reporting garbage, which is the apparatus working. So `auto` is LAST here
with nothing behind it, and the reference side can be read at last.

RENUM's typed tail also needs its oracle: `10 RENUM 100:PRINT"[R1]"` answered
`Undefined line 100 in 10` on zerobas, and whether that is the verb or a
divergence is the reference's to say.
"""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    ("inp.file", 'OPEN"HI.TXT"FOR INPUT AS#1:INPUT#1,A$:CLOSE#1:PRINT"[I";LEN(A$);"]"'),
    ("inp.ctl",  'OPEN"HI.TXT"FOR INPUT AS#1:A$="":CLOSE#1:PRINT"[I";LEN(A$);"]"'),
    ("ren.100",  'RENUM 100:PRINT"[R1]"'),
    ("ren.bare", 'RENUM:PRINT"[R2]"'),
    ("ren.ctl",  'A=1:PRINT"[R3]"'),
    ("auto.row", 'AUTO 100'),          # LAST: nothing behind it to poison
]
for name in (sys.argv[1:] or ["zb", "cf3300"]):
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
