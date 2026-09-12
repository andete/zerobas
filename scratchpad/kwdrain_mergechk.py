#!/usr/bin/env python3
"""Does a program CONTINUE after MERGE? zerobas printed [ 7 ] and the CF-3300
printed nothing at all -- with the write timing already ruled out (the reference
reached its Ok prompt). Three arms separate "MERGE stopped the program" from
"the merge did not happen" from "GOSUB failed"."""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    # arm 1: does ANY statement after MERGE run, merged line or not?
    ("after",  ['10 OPEN"N.BAS"FOR OUTPUT AS#1', '20 PRINT#1,"100 A=7:RETURN"',
                '30 CLOSE', '40 MERGE"N.BAS"', '50 PRINT"[M1]"', 'RUN']),
    # arm 2: did the merge LAND? asked from direct mode, after the program ended.
    ("landed", ['PRINT"[M";A;"]"']),
    ("listed", ['LIST 100']),
    # arm 3: the same file merged from DIRECT mode, then GOSUB from a program.
    ("direct", ['MERGE"N.BAS"']),
    ("gosub",  ['10 GOSUB 100', '20 PRINT"[M";A;"]"', 'RUN']),
]
for name in (sys.argv[1:] or ["zb"]):
    cfg = probe_sides.sides(name)[name]
    kw, tmp = {}, None
    if probe_sides.diska(name, TEST_DSK):
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False); tmp.close()
        shutil.copy(TEST_DSK, tmp.name); kw["diska"] = tmp.name
    try:
        # NO reset between cases: `landed`/`listed`/`gosub` ask about the state
        # the case before them left behind. That is the whole point.
        caps = omsx_repl.run_cases(cfg["machine"], [(t, ls) for t, ls in CASES],
                                   batch=True, reset=(), boot=cfg["boot"],
                                   step=5.0, cap_gap=20.0, timeout=900.0, **kw)
    finally:
        if tmp: os.unlink(tmp.name)
    print("=== %s" % name)
    for (tag, ls), cap in zip(CASES, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        print("  %-7s | %s" % (tag, txt[-170:]))
    sys.stdout.flush()
