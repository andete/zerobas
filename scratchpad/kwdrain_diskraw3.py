#!/usr/bin/env python3
"""Round 3: the packer question (does BLOAD/BSAVE eat the rest of its PROGRAM
line, the way a direct-mode BLOAD does?), CLOSE's blind-shape control, DSKO$'s
round trip, MERGE on an ASCII save, RUN's line-number form, and IPL."""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    # does a PROGRAM-line BLOAD eat the statements after it on the same line?
    ("bl.same",  ['10 POKE&HC000,7:BLOAD"PROG.BIN":A=PEEK(&HC000)',
                  '20 PRINT"[X";A;"]"', 'RUN']),
    ("bs.same",  ['10 POKE&HC800,99:BSAVE"P.BIN",&HC800,&HC800:POKE&HC800,7',
                  '20 BLOAD"P.BIN":A=PEEK(&HC800)', '30 PRINT"[X";A;"]"', 'RUN']),
    # CLOSE's blind shape: the same row with the CLOSE removed.
    ("close.no", ['OPEN"Y.TXT"FOR OUTPUT AS#1:PRINT#1,"ABC":OPEN"Y.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE:PRINT"[X";A;"]"']),
    # DSKO$: poke the buffer, write sector 7, re-read it, read the byte back.
    ("dsko.rt",  ['10 A$=DSKI$(0,7):B=PEEK(&HF351)+256*PEEK(&HF352)',
                  '20 POKE B,88:DSKO$0,7', '30 A$=DSKI$(0,0):A$=DSKI$(0,7)',
                  '40 A=PEEK(B):PRINT"[X";A;"]"', 'RUN']),
    # MERGE needs an ASCII save; does it continue the program after merging?
    ("merge.a",  ['10 A=1', '20 SAVE"M.BAS",A', '30 MERGE"M.BAS"',
                  '40 PRINT"[X9]"', 'RUN']),
    # RUN <line>: the second pass takes the branch the first cannot.
    ("run.n",    ['10 POKE&HE001,0', '20 POKE&HE001,PEEK(&HE001)+1',
                  '30 IF PEEK(&HE001)>1 THEN PRINT"[X";PEEK(&HE001);"]":END',
                  '40 RUN 20', 'RUN']),
    ("ipl",      ['IPL']),
    ("lpos",     ['PRINT"[X";LPOS(0);"]"']),
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
    print("  %-9s %-6s | %s" % (tag, m[-1] if m else "NONE", txt[-160:]))
