#!/usr/bin/env python3
"""D-KWDRAIN disk slice: measure every candidate disk/tape readback BEFORE a row
is written, with the test image MOUNTED (a writable private copy per machine).

The standard this drain adopted: a readback must be PROVED to move when the verb
stops working. Each `*.ctl` case here is the blind-shape control for the row
above it -- what the screen would read if the verb parsed and did nothing.

    python3 scratchpad/kwdrain_diskmount.py [zb|cf3300|vg8020 ...] [--only tag,tag]
"""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides

TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")

# (tag, lines) -- direct-mode unless the list starts with a numbered line.
CASES = [
    # --- DSKF: batch 4 measured DSKF(0)==0 with NO DISK INSERTED and read that
    # as "reads 0 like a stub". Re-measured with the image in.
    ("dskf.1",     ['PRINT"[X";DSKF(1);"]"']),
    ("dskf.0",     ['PRINT"[X";DSKF(0);"]"']),
    # --- LOF / LOC / EOF need an OPEN channel; HI.TXT is 26 bytes.
    ("lof",        ['OPEN"HI.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[X";A;"]"']),
    ("loc",        ['OPEN"HI.TXT"FOR INPUT AS#1:A$=INPUT$(10,#1):A=LOC(1):CLOSE#1:PRINT"[X";A;"]"']),
    ("eof.start",  ['OPEN"HI.TXT"FOR INPUT AS#1:A=EOF(1):CLOSE#1:PRINT"[X";A;"]"']),
    ("eof.end",    ['OPEN"HI.TXT"FOR INPUT AS#1:A$=INPUT$(26,#1):A=EOF(1):CLOSE#1:PRINT"[X";A;"]"']),
    # --- CLOSE: reopening the SAME channel only works if the close happened.
    ("close.reop", ['OPEN"HI.TXT"FOR INPUT AS#1:CLOSE#1:OPEN"HI.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[X";A;"]"']),
    ("close.ctl",  ['OPEN"HI.TXT"FOR INPUT AS#1:OPEN"HI.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[X";A;"]"']),
    # --- BLOAD: PROG.BIN loads at $C000 and its first byte is $3E (62).
    ("bload.ctl",  ['POKE&HC000,7:A=PEEK(&HC000):PRINT"[X";A;"]"']),
    ("bload",      ['POKE&HC000,7:BLOAD"PROG.BIN":A=PEEK(&HC000):PRINT"[X";A;"]"']),
    # --- DSKI$: the sector lands in the buffer at (F351); root dir = sector 7.
    ("dski.ctl",   ['B=PEEK(&HF351)+256*PEEK(&HF352):A=PEEK(B):PRINT"[X";A;"]"']),
    ("dski.dir",   ['A$=DSKI$(0,7):B=PEEK(&HF351)+256*PEEK(&HF352):A=PEEK(B):PRINT"[X";A;"]"']),
    ("dski.boot",  ['A$=DSKI$(0,0):B=PEEK(&HF351)+256*PEEK(&HF352):A=PEEK(B):PRINT"[X";A;"]"']),
    # --- FILES: the listing itself is the behaviour; CSRLIN counts its rows.
    ("files.ctl",  ['CLS:A=CSRLIN:PRINT"[X";A;"]"']),
    ("files",      ['CLS:FILES:A=CSRLIN:PRINT"[X";A;"]"']),
    # --- BSAVE: a round trip through the disk, read back at a DIFFERENT value.
    ("bsave.rt",   ['POKE&HC800,99:BSAVE"O.BIN",&HC800,&HC800:POKE&HC800,7:BLOAD"O.BIN":A=PEEK(&HC800):PRINT"[X";A;"]"']),
    # --- SAVE: the saved file's own length, read back through a channel.
    ("save.lof",   ['10 A=1', '20 SAVE"S.BAS"', '30 OPEN"S.BAS"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[X";A;"]"', 'RUN']),
    # --- COPY: the copy's length is the source's.
    ("copy",       ['COPY"HI.TXT"TO"H2.TXT":OPEN"H2.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[X";A;"]"']),
    # --- KILL: the freed space is the behaviour (TEST.BIN is two clusters).
    ("kill.dskf",  ['A=DSKF(1):KILL"TEST.BIN":B=DSKF(1):PRINT"[X";B-A;"]"']),
    # --- LSET / RSET: justification inside a FIELDed buffer.
    ("lset",       ['OPEN"R.DAT"AS#1:FIELD#1,4 AS A$:LSET A$="B":A=ASC(A$):CLOSE#1:PRINT"[X";A;"]"']),
    ("rset",       ['OPEN"R.DAT"AS#1:FIELD#1,4 AS A$:RSET A$="B":A=ASC(A$):CLOSE#1:PRINT"[X";A;"]"']),
    ("rset.4",     ['OPEN"R.DAT"AS#1:FIELD#1,4 AS A$:RSET A$="B":A=ASC(MID$(A$,4,1)):CLOSE#1:PRINT"[X";A;"]"']),
    # --- the refuse-on-sight words: ERR 5 with a disk ROM, Syntax error on a stub.
    ("set",        ['SET PASSWORD']),
    ("cmd",        ['CMD"X"']),
    ("attr",       ['A$=ATTR$(0)']),
]

def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--only"):
            only = set(a.split("=", 1)[1].split(",")) if "=" in a else None
    names = argv or ["zb"]
    sel = [c for c in CASES if only is None or c[0] in only]
    for name in names:
        cfg = probe_sides.sides(name)[name]
        kw = {}
        tmp = None
        img = probe_sides.diska(name, TEST_DSK)
        if img:
            tmp = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False)
            tmp.close()
            shutil.copy(TEST_DSK, tmp.name)   # never mount the original
            kw["diska"] = tmp.name
        try:
            caps = omsx_repl.run_cases(cfg["machine"], [(t, ls) for t, ls in sel],
                                       batch=True, reset=cfg["reset"] + ("CLS",),
                                       boot=cfg["boot"], **kw)
        finally:
            if tmp:
                os.unlink(tmp.name)
        print("=== %s (%s)  disk=%s" % (name, cfg["machine"], "YES" if img else "no"))
        for (tag, _), cap in zip(sel, caps):
            txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
            m = re.findall(r"\[X\s*(-?\d+)\s*\]", txt)
            e = re.findall(r"(?i)([A-Za-z][A-Za-z /]*(?:error|call|number|found|open|name|space|record))",
                           txt)
            print("  %-11s %-8s %s" % (tag, m[-1] if m else "NONE",
                                       "; ".join(sorted(set(x.strip().lower() for x in e)))[:70]))
        sys.stdout.flush()

main()
