#!/usr/bin/env python3
"""The DIRECT-mode half of the command-level contract, asked BEFORE the run-mode
fix, so a fix aimed at a program cannot silently change a typed line.

`end_line_end` sets ENDFLAG, which the run loop tests -- but a TYPED line is also
a statement stream, and NEW/LIST already set the same flag from direct mode. So:
does a statement after a typed LOAD / MERGE run today, and does it run on the
reference? Whatever the answer, both sides have to keep agreeing after the fix.
"""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    ("mk",     ['10 OPEN"N.BAS"FOR OUTPUT AS#1', '20 PRINT#1,"100 END"', '30 CLOSE', 'RUN']),
    ("d.load", ['POKE&HD002,0:LOAD"PROG.BAS":POKE&HD002,55']),
    ("d.load?",['PRINT"[L";PEEK(&HD002);"]"']),
    ("d.merg", ['POKE&HD002,0:MERGE"N.BAS":POKE&HD002,55']),
    ("d.merg?",['PRINT"[M";PEEK(&HD002);"]"']),
    ("d.new",  ['POKE&HD002,0:NEW:POKE&HD002,55']),       # the shipped precedent
    ("d.new?", ['PRINT"[N";PEEK(&HD002);"]"']),
]
for name in (sys.argv[1:] or ["zb", "cf3300"]):
    cfg = probe_sides.sides(name)[name]
    kw, tmp = {}, None
    if probe_sides.diska(name, TEST_DSK):
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False); tmp.close()
        shutil.copy(TEST_DSK, tmp.name); kw["diska"] = tmp.name
    pre = ("", "SCREEN 0") if name == "cf3300" else ()
    try:
        caps = omsx_repl.run_cases(cfg["machine"], [(t, ls) for t, ls in CASES],
                                   batch=True, reset=pre, boot=cfg["boot"],
                                   step=4.0, cap_gap=20.0, timeout=900.0, **kw)
    finally:
        if tmp: os.unlink(tmp.name)
    print("=== %s" % name)
    for (tag, ls), cap in zip(CASES, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        m = re.findall(r"\[[LMN]\s*(-?\d+)\s*\]", txt)
        print("  %-8s %-5s | %s" % (tag, m[-1] if m else "-", txt[-90:]))
    sys.stdout.flush()
