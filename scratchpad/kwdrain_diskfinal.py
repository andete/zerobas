#!/usr/bin/env python3
"""D-KWDRAIN disk slice — the FINAL row shapes, in the order the sweep will run
them, measured on zerobas AND on the disk-equipped reference.

ORDER IS PART OF THE ROW SET. `dsko` rewrites the first byte of the root
directory and `kill` deletes a file, so every reading row comes first; `ipl` is
last because a reference that hangs on it must not take another row with it
[[apparatus-is-part-of-the-measurement]].

    python3 scratchpad/kwdrain_diskfinal.py zb cf3300
"""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")

# (tag, exec line) -- stored mode, exactly as a kwsweep row is delivered.
CASES = [
    ("dskf",  'PRINT"[";DSKF(1)>0;"]"'),
    ("dskfv", 'PRINT"[";DSKF(1);"]"'),
    ("lof",   'OPEN"HI.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"'),
    ("loc",   'OPEN"HI.TXT"FOR INPUT AS#1:A$=INPUT$(10,#1):A=LOC(1):CLOSE#1:PRINT"[";A;"]"'),
    ("eof",   'OPEN"HI.TXT"FOR INPUT AS#1:A$=INPUT$(26,#1):A=EOF(1):CLOSE#1:PRINT"[";A;"]"'),
    ("files", 'CLS:FILES"HI.TXT":A=CSRLIN:PRINT"[F";A;"]"'),
    ("dski",  'A$=DSKI$(0,7):B=PEEK(&HF351)+256*PEEK(&HF352):A=PEEK(B):PRINT"[";A;"]"'),
    ("bload", 'POKE&HC000,7:BLOAD"PROG.BIN":A=PEEK(&HC000):PRINT"[";A;"]"'),
    ("runkw", 'POKE&HE001,0:POKE&HE001,PEEK(&HE001)+1:IF PEEK(&HE001)<2 THEN RUN 20:PRINT"[";PEEK(&HE001);"]"'),
    ("close", 'OPEN"W.TXT"FOR OUTPUT AS#1:PRINT#1,"ABC":CLOSE#1:OPEN"W.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"'),
    ("bsave", 'POKE&HC800,99:BSAVE"O.BIN",&HC800,&HC800:POKE&HC800,7:BLOAD"O.BIN":A=PEEK(&HC800):PRINT"[";A;"]"'),
    ("save",  'A=1:SAVE"S.BAS":OPEN"S.BAS"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"'),
    ("lset",  'OPEN"R.DAT"AS#1:FIELD#1,4 AS A$:LSET A$="B":A=ASC(A$):CLOSE#1:PRINT"[";A;"]"'),
    ("rset",  'OPEN"R.DAT"AS#1:FIELD#1,4 AS A$:RSET A$="B":A=ASC(A$):CLOSE#1:PRINT"[";A;"]"'),
    ("copy",  'COPY"HI.TXT" TO "H2.TXT":OPEN"H2.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"'),
    ("kill",  'A=DSKF(1):KILL"PROG2.BAS":B=DSKF(1):PRINT"[";B-A;"]"'),
    ("merge", 'OPEN"N.BAS"FOR OUTPUT AS#1:PRINT#1,"100 A=7:RETURN":CLOSE:MERGE"N.BAS":GOSUB 100:PRINT"[";A;"]"'),
    ("dsko",  'A$=DSKI$(0,7):B=PEEK(&HF351)+256*PEEK(&HF352):POKE B,88:DSKO$0,7:A$=DSKI$(0,0):A$=DSKI$(0,7):A=PEEK(B):PRINT"[";A;"]"'),
    ("setkw", 'SET PASSWORD'),
    ("cmdkw", 'CMD"X"'),
    ("iplkw", 'IPL'),
]

def main():
    for name in (sys.argv[1:] or ["zb"]):
        cfg = probe_sides.sides(name)[name]
        kw = {}
        tmp = None
        if probe_sides.diska(name, TEST_DSK):
            tmp = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False); tmp.close()
            shutil.copy(TEST_DSK, tmp.name)
            kw["diska"] = tmp.name
        specs = [("stored", omsx_repl.as_stored(line)) for _, line in CASES]
        try:
            caps = omsx_repl.run_cases(cfg["machine"], specs, batch=True,
                                       reset=cfg["reset"] + ("NEW", "CLS"),
                                       boot=cfg["boot"], **kw)
        finally:
            if tmp:
                os.unlink(tmp.name)
        print("=== %s (%s)" % (name, cfg["machine"]))
        for (tag, line), cap in zip(CASES, caps):
            txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
            m = re.findall(r"\[F?\s*(-?\d+)\s*\]", txt)
            print("  %-6s %-6s | %s" % (tag, m[-1] if m else "NONE", txt[-110:]))
        sys.stdout.flush()

main()
