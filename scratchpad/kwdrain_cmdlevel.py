#!/usr/bin/env python3
"""D-MERGERET: the "return to command level" contract, swept across all three
verbs that share it, BEFORE any of them is changed.

`MERGE` is the filed defect. `LOAD` and `RUN"file"` are its neighbours, and the
standing lesson (D-DFEND) is that verbs filed separately can be one tail.

The readback is ONE RAM CELL, $D002, and it separates three outcomes because each
writes a different value:
    0   the statement after the verb never ran and nothing else did
    55  the statement AFTER the verb ran  <- the divergence MERGE shows
    123 the LOADED program ran (PROG.BAS's own landmark)
⚠️ LOAD REPLACES THE PROGRAM, so its line 30 does not survive the load at all;
that is the point of asking the cell rather than asking for a marker the vanished
line would have printed.
"""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    ("mk",       ['10 OPEN"N.BAS"FOR OUTPUT AS#1', '20 PRINT#1,"100 END"',
                  '30 CLOSE', 'RUN']),
    ("load",     ['NEW', '10 POKE&HD002,0', '20 LOAD"PROG.BAS"', '30 POKE&HD002,55', 'RUN']),
    ("load?",    ['PRINT"[L";PEEK(&HD002);"]"']),
    ("merge",    ['NEW', '10 POKE&HD002,0', '20 MERGE"N.BAS"', '30 POKE&HD002,55', 'RUN']),
    ("merge?",   ['PRINT"[M";PEEK(&HD002);"]"']),
    ("runf",     ['NEW', '10 POKE&HD002,0', '20 RUN"PROG.BAS"', '30 POKE&HD002,55', 'RUN']),
    ("runf?",    ['PRINT"[R";PEEK(&HD002);"]"']),
]
for name in (sys.argv[1:] or ["zb", "cf3300"]):
    cfg = probe_sides.sides(name)[name]
    kw, tmp = {}, None
    if probe_sides.diska(name, TEST_DSK):
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False); tmp.close()
        shutil.copy(TEST_DSK, tmp.name); kw["diska"] = tmp.name
    # reset is the SCREEN prologue only -- NEW is typed per case where it is
    # wanted, because the readback cases must see what the case before them left.
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
        m = re.findall(r"\[[LMR]\s*(-?\d+)\s*\]", txt)
        print("  %-7s %-5s | %s" % (tag, m[-1] if m else "-", txt[-95:]))
    sys.stdout.flush()
