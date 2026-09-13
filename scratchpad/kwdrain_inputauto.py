#!/usr/bin/env python3
"""D-KWGET's lesson applied to the remaining six: is each one blocked by what its
neighbour is blocked by, or only by its NAME?

  INPUT  -- has a FILE form (`INPUT #n, var`) that needs no keystroke at all.
  AUTO   -- scored itself correctly once and took 21 unrelated rows down with it.
            The verb was never the problem; the POSITION was. Last row, no
            neighbours to poison.
  RENUM  -- filed as "stops the program, so no statement after it runs". Measured
            for a STORED program. Does it stop a TYPED line too?

⚠️ `auto` IS LAST IN THIS LIST ON PURPOSE, and the two cases after it are its
blast radius: if line-entry mode really does swallow what follows, they read as
nothing and that is the measurement.
"""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    # INPUT: the fixture's own line is `Hello from zerobas-disk!` + CRLF
    ("inp.file", 'OPEN"HI.TXT"FOR INPUT AS#1:INPUT#1,A$:CLOSE#1:PRINT"[I";LEN(A$);"]"'),
    ("inp.ctl",  'OPEN"HI.TXT"FOR INPUT AS#1:A$="":CLOSE#1:PRINT"[I";LEN(A$);"]"'),
    # RENUM in a TYPED line: does the tail after it run?
    ("ren.tail", 'RENUM 100:PRINT"[R1]"'),
    ("ren.ctl",  'REM X:PRINT"[R1]"'),
    # AUTO last, with two sacrificial rows behind it to measure the blast radius
    ("auto.row", 'AUTO 100'),
    ("blast1",   'PRINT"[B1]"'),
    ("blast2",   'PRINT"[B2]"'),
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
