#!/usr/bin/env python3
"""The rows that WRITE came back blank on the CF-3300 (and `kill` on zerobas too).
Hypothesis: not a refusal -- the capture fires before the write finishes. Same
rows, a bigger cap_gap. Plus the FILES readback, whose CSRLIN form measured the
MACHINES (the CF-3300 shows the function-key line, so the screen is a row
shorter and the cursor lands elsewhere), not the verb."""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    ("close", 'OPEN"W.TXT"FOR OUTPUT AS#1:PRINT#1,"ABC":CLOSE#1:OPEN"W.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"'),
    ("bsave", 'POKE&HC800,99:BSAVE"O.BIN",&HC800,&HC800:POKE&HC800,7:BLOAD"O.BIN":A=PEEK(&HC800):PRINT"[";A;"]"'),
    ("save",  'A=1:SAVE"S.BAS":OPEN"S.BAS"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"'),
    ("copy",  'COPY"HI.TXT" TO "H2.TXT":OPEN"H2.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"'),
    ("kill",  'A=DSKF(1):KILL"PROG2.BAS":B=DSKF(1):PRINT"[";B-A;"]"'),
    ("merge", 'OPEN"N.BAS"FOR OUTPUT AS#1:PRINT#1,"100 A=7:RETURN":CLOSE:MERGE"N.BAS":GOSUB 100:PRINT"[";A;"]":END'),
    ("filesm",'FILES"NOSUCH.XYZ"'),
    ("filesh",'FILES"HI.TXT":PRINT"[8]"'),
]
for name in (sys.argv[1:] or ["zb"]):
    cfg = probe_sides.sides(name)[name]
    kw = {}
    tmp = None
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
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        m = re.findall(r"\[\s*(-?\d+)\s*\]", txt)
        print("  %-7s %-6s | %s" % (tag, m[-1] if m else "NONE", txt[-130:]))
    sys.stdout.flush()
