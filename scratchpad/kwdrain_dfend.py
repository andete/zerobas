#!/usr/bin/env python3
"""Before changing `df_end` (sub/dirverb.asm), the one arm neither reading covers:
what happens to the printer head when LFILES matches NOTHING.

`df_end` is reached whether or not the walk emitted an entry, so a fix that
zeroes LPTPOS unconditionally is only right if the reference does too. R-LF4/R-LF6
say a no-match prints `File not found` on the SCREEN -- so nothing reaches the
printer, and the head should stay where it was parked. Asked, not assumed.

  lf.none  head parked at 2, LFILES with a pattern that matches nothing
  lf.mid   head parked at 2, LFILES that matches everything   (the known arm)
  f.one    FILES with one match, then PRINT  -- the SCREEN half, a THIRD entry
           besides HI.TXT and the bare listing
"""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    ("lf.none", ['10 LPRINT"AB";', '20 LFILES"NOSUCH.XYZ"',
                 '30 PRINT"[P";LPOS(0);"]"', 'RUN']),
    ("lf.mid",  ['10 LPRINT"AB";', '20 LFILES',
                 '30 PRINT"[P";LPOS(0);"]"', 'RUN']),
    ("f.one",   ['10 FILES"PROG.BIN"', '20 PRINT"[P";CSRLIN;",";POS(0);"]"', 'RUN']),
]
for name in (sys.argv[1:] or ["zb", "cf3300"]):
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
        rows = [raw[r*40:(r+1)*40].rstrip() for r in range(24)] if raw else []
        screen = " | ".join(r.strip() for r in rows if r.strip())[-95:]
        blob = open(log.name, "rb").read()
        print("  %-8s log=%3d B %-18r  %s" % (lab, len(blob), blob[-12:], screen))
        os.unlink(log.name)
        sys.stdout.flush()
