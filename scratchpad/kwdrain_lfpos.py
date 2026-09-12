#!/usr/bin/env python3
"""Two questions the log reading opened.

(1) zerobas's `LFILES` printed 75 bytes ending in CRLF and left `LPOS(0)` at 2 --
    the head counter did not move. Does the CF-3300, which is the oracle for a
    Disk-BASIC verb, leave it at 0? If so that is a divergence, and a FILED
    divergence attributes the keyword without any new capture apparatus.
(2) `LLIST` and `LFILES` both stop a PROGRAM, which is why line 30 never ran.
    Do they stop a DIRECT-mode line too? If not, a one-line direct row can read
    LPOS back and the printer LOG is not needed for them either.
"""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
# direct mode: the whole row is ONE typed line, exactly a kwsweep direct row
CASES = [
    ("d.ctl",    ['LPRINT"AB";:PRINT"[P";LPOS(0);"]"']),
    ("d.llist",  ['LPRINT"AB";:LLIST:PRINT"[P";LPOS(0);"]"']),
    ("d.lfiles", ['LPRINT"AB";:LFILES:PRINT"[P";LPOS(0);"]"']),
    ("d.lfbare", ['LFILES:PRINT"[P";LPOS(0);"]"']),
    ("d.lpr2",   ['LPRINT"AB":PRINT"[P";LPOS(0);"]"']),   # LPRINT with CRLF -> 0
]
for name in (sys.argv[1:] or ["zb"]):
    cfg = probe_sides.sides(name)[name]
    print("=== %s" % name)
    for lab, lines in CASES:
        log = tempfile.NamedTemporaryFile(suffix=".prn", delete=False); log.close()
        kw = {}
        if probe_sides.diska(name, TEST_DSK):
            d = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False); d.close()
            shutil.copy(TEST_DSK, d.name); kw["diska"] = d.name
        caps = omsx_repl.run_cases(cfg["machine"], [("d", list(cfg["reset"]) + lines)],
                                   batch=False, reset=(), boot=cfg["boot"],
                                   step=4.0, cap_gap=25.0, timeout=900.0,
                                   prologue=(f"set printerlogfilename {{{log.name}}}",
                                             "plug printerport logger"), **kw)
        raw = caps[0]
        tail = omsx_repl.screen_tail(raw, lines[-1])
        blob = open(log.name, "rb").read()
        print("  %-9s tail=%-28r log=%3d B %r" % (lab, tail, len(blob), blob[:70]))
        os.unlink(log.name)
        sys.stdout.flush()
