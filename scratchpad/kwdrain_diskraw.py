#!/usr/bin/env python3
"""Raw screen dump for the kwdrain disk candidates that printed no marker."""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    ("bload",   ['BLOAD"PROG.BIN":A=PEEK(&HC000):PRINT"[X";A;"]"']),
    ("bloadA",  ['BLOAD"A:PROG.BIN":A=PEEK(&HC000):PRINT"[X";A;"]"']),
    ("bsave",   ['BSAVE"O.BIN",&HC800,&HC800']),
    ("bsave2",  ['POKE&HC800,99:BSAVE"O.BIN",&HC800,&HC80F:PRINT"[X9]"']),
    ("copy",    ['COPY"HI.TXT" TO "H2.TXT":PRINT"[X9]"']),
    ("kill",    ['KILL"TEST.BIN":PRINT"[X9]"']),
    ("kill2",   ['A=DSKF(1):KILL"TEST.BIN":B=DSKF(1):PRINT"[X";B-A;"]"']),
    ("loc2",    ['OPEN"TEST.BIN"FOR INPUT AS#1:A$=INPUT$(200,#1):A=LOC(1):CLOSE#1:PRINT"[X";A;"]"']),
    ("loc0",    ['OPEN"TEST.BIN"FOR INPUT AS#1:A=LOC(1):CLOSE#1:PRINT"[X";A;"]"']),
]
name = "zb"
cfg = probe_sides.sides(name)[name]
tmp = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False); tmp.close()
shutil.copy(TEST_DSK, tmp.name)
try:
    caps = omsx_repl.run_cases(cfg["machine"], [(t, ls) for t, ls in CASES],
                               batch=True, reset=cfg["reset"] + ("CLS",),
                               boot=cfg["boot"], diska=tmp.name)
finally:
    os.unlink(tmp.name)
for (tag, ls), cap in zip(CASES, caps):
    txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
    print("--- %-8s %s" % (tag, txt[-220:]))
