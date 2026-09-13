#!/usr/bin/env python3
"""D-KWGET: the two words left that need no new apparatus.

`GET` is MSX1's RANDOM-FILE record read (`GET #n[,record]`), not a keyboard verb,
and `PUT` already ships — so a round trip fits one row. The arms are built so the
BLIND SHAPE is inside the same reading: the buffer is overwritten to "Z" between
the PUT and the GET, and BOTH values are printed. A GET that did nothing leaves
the second reading at 90 (Z); a real one restores 66 (B).

`CALL` is an honest maybe: if an UNKNOWN extension answers `Syntax error`, so does
a machine with no CALL at all, and the row would be blind. ⚠️ `CALL SYSTEM` and
`CALL FORMAT` are NEVER invoked here — one exits to DOS, one formats the disk.
"""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    # A = the buffer after the overwrite (90 = "Z"), B = after the GET (66 = "B")
    ("get.rt",   'OPEN"R.DAT"AS#1:FIELD#1,4 AS A$:LSET A$="B":PUT#1,1:LSET A$="Z":A=ASC(A$):GET#1,1:B=ASC(A$):CLOSE#1:PRINT"[G";A;B;"]"'),
    # the blind shape: identical, with the GET removed -- B must stay 90
    ("get.ctl",  'OPEN"R.DAT"AS#1:FIELD#1,4 AS A$:LSET A$="B":PUT#1,1:LSET A$="Z":A=ASC(A$):B=ASC(A$):CLOSE#1:PRINT"[G";A;B;"]"'),
    ("call.zzq", 'CALL ZZQ'),
    ("call.bare",'CALL'),
    ("call.stub",'ZZQQ ZZQ'),          # what an ABSENT keyword's line looks like
]
for name in (sys.argv[1:] or ["zb", "cf3300", "vg8020"]):
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
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        tail = omsx_repl.screen_tail(cap, "RUN")
        print("  %-10s tail=%r" % (tag, tail))
    sys.stdout.flush()
