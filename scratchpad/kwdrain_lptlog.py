#!/usr/bin/env python3
"""The LPOS trick failed for `LFILES` (head unchanged at 2) and `LLIST` printed
nothing to the SCREEN. Two readings separate "the verb printed nothing" from
"the screen could not see it": the printer LOG itself, one boot per case so each
log is that case's own (batched, the log ACCUMULATES -- D-BATCH2)."""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    ("ctl",    ['10 LPRINT"AB";', '20 PRINT"[P";LPOS(0);"]"', 'RUN']),
    ("llist",  ['10 LPRINT"AB";', '20 LLIST', '30 PRINT"[P";LPOS(0);"]"', 'RUN']),
    ("lfiles", ['10 LPRINT"AB";', '20 LFILES', '30 PRINT"[P";LPOS(0);"]"', 'RUN']),
    ("lfdir",  ['10 LFILES', '20 PRINT"[P";LPOS(0);"]"', 'RUN']),
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
        txt = re.sub(r"\s+", " ", caps[0] if isinstance(caps[0], str) else str(caps[0]))
        after = txt.split("RUN", 1)[1] if "RUN" in txt else txt
        m = re.findall(r"\[P\s*(-?\d+)\s*\]", after)
        blob = open(log.name, "rb").read()
        print("  %-7s LPOS=%-5s log=%3d B  %r" % (lab, m[-1] if m else "NONE",
                                                  len(blob), blob[:90]))
        os.unlink(log.name)
        sys.stdout.flush()
