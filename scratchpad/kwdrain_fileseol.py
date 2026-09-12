#!/usr/bin/env python3
"""The `files` kwsweep row came back DIVERGENT on the ROW BOUNDARY, not the text:
ref `HI      .TXT [8]` on ONE screen row, zerobas `HI      .TXT` then `[8]` on
two. This asks what the cursor does after a directory listing, per screen row,
so the finding is a mechanism and not a diff."""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    ("one",   'FILES"HI.TXT":PRINT"<B>"'),
    ("onep",  'FILES"HI.TXT":PRINT"<";CSRLIN;",";POS(0);">"'),
    ("all",   'FILES:PRINT"<B>"'),
    ("allp",  'FILES:PRINT"<";CSRLIN;",";POS(0);">"'),
    ("none",  'PRINT"<";CSRLIN;",";POS(0);">"'),
]
for name in (sys.argv[1:] or ["zb"]):
    cfg = probe_sides.sides(name)[name]
    kw, tmp = {}, None
    if probe_sides.diska(name, TEST_DSK):
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False); tmp.close()
        shutil.copy(TEST_DSK, tmp.name); kw["diska"] = tmp.name
    specs = [("stored", omsx_repl.as_stored(l)) for _, l in CASES]
    try:
        caps = omsx_repl.run_cases(cfg["machine"], specs, batch=True,
                                   reset=cfg["reset"] + ("NEW", "CLS"),
                                   boot=cfg["boot"], step=5.0, cap_gap=20.0,
                                   timeout=900.0, **kw)
    finally:
        if tmp: os.unlink(tmp.name)
    print("=== %s" % name)
    for (tag, l), cap in zip(CASES, caps):
        print("  --- %s" % tag)
        rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
        for i, r in enumerate(rows):
            if r.strip():
                print("      %2d |%s|" % (i, r))
    sys.stdout.flush()
