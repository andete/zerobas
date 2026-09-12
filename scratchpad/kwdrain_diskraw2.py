#!/usr/bin/env python3
"""Round 2: the shapes round 1 left open -- BLOAD/BSAVE need their own LINE
(a direct-mode BLOAD eats the rest of the line), CLOSE needs a readback that
MOVES, and LOC/COPY/KILL need controls that are not clobbered by a neighbour."""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    ("bload.st",  ['10 POKE&HC000,7', '20 BLOAD"PROG.BIN"',
                   '30 A=PEEK(&HC000):PRINT"[X";A;"]"', 'RUN']),
    ("bsave.st",  ['10 POKE&HC800,99', '20 BSAVE"O.BIN",&HC800,&HC800',
                   '30 POKE&HC800,7', '40 BLOAD"O.BIN"',
                   '50 A=PEEK(&HC800):PRINT"[X";A;"]"', 'RUN']),
    ("loc.0",     ['OPEN"HI.TXT"FOR INPUT AS#1:A=LOC(1):CLOSE#1:PRINT"[X";A;"]"']),
    ("loc.10",    ['OPEN"HI.TXT"FOR INPUT AS#1:A$=INPUT$(10,#1):A=LOC(1):CLOSE#1:PRINT"[X";A;"]"']),
    ("close.flu", ['OPEN"W.TXT"FOR OUTPUT AS#1:PRINT#1,"ABC":CLOSE#1:OPEN"W.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[X";A;"]"']),
    ("close.ctl", ['OPEN"V.TXT"FOR OUTPUT AS#1:PRINT#1,"ABC":OPEN"V.TXT"FOR INPUT AS#2:A=LOF(2):CLOSE:PRINT"[X";A;"]"']),
    ("copy.lof",  ['COPY"HI.TXT" TO "H2.TXT":OPEN"H2.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[X";A;"]"']),
    ("copy.ns",   ['COPY"HI.TXT"TO"H3.TXT":OPEN"H3.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[X";A;"]"']),
    ("kill.d",    ['A=DSKF(1):KILL"PROG2.BAS":B=DSKF(1):PRINT"[X";B-A;"]"']),
    ("kill.ctl",  ['A=DSKF(1):B=DSKF(1):PRINT"[X";B-A;"]"']),
    ("merge",     ['10 PRINT"[X1]"', '20 MERGE"PROG.BAS"', 'RUN', 'PRINT"[X";PEEK(&HD002);"]"']),
    ("run.file",  ['10 POKE&HD002,0', '20 RUN"PROG.BAS"', 'RUN', 'PRINT"[X";PEEK(&HD002);"]"']),
]
name = sys.argv[1] if len(sys.argv) > 1 else "zb"
cfg = probe_sides.sides(name)[name]
tmp = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False); tmp.close()
shutil.copy(TEST_DSK, tmp.name)
try:
    caps = omsx_repl.run_cases(cfg["machine"], [(t, ls) for t, ls in CASES],
                               batch=True, reset=cfg["reset"] + ("CLS",),
                               boot=cfg["boot"], diska=tmp.name)
finally:
    os.unlink(tmp.name)
print("=== %s" % name)
for (tag, ls), cap in zip(CASES, caps):
    txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
    m = re.findall(r"\[X\s*(-?\d+)\s*\]", txt)
    print("  %-10s %-6s | %s" % (tag, m[-1] if m else "NONE", txt[-150:]))
