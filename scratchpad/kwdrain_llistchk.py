#!/usr/bin/env python3
"""What exactly should an `LLIST` kwsweep row assert? The verb's only output is
the printer LOG, so the row's reading is the log bytes — and the program being
listed IS the row's own stored program, which makes the expected text something I
can choose rather than something I have to hope agrees.

Arms, boot-per-case so each log is its own (batched, the log ACCUMULATES):
  llist.bare   `10 LLIST`      -- the minimal row: the listing is one line
  llist.rem    `10 LLIST:REM ZQ8`  -- a distinctive tail, to see token spacing
  ctl.noverb   `10 REM ZQ8`    -- the BLIND SHAPE: no LLIST, so an empty log
"""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    ("llist.bare", ['10 LLIST', 'RUN']),
    ("llist.rem",  ['10 LLIST:REM ZQ8', 'RUN']),
    ("ctl.noverb", ['10 REM ZQ8', 'RUN']),
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
                                   step=4.0, cap_gap=20.0, timeout=900.0,
                                   prologue=(f"set printerlogfilename {{{log.name}}}",
                                             "plug printerport logger"), **kw)
        blob = open(log.name, "rb").read()
        screen = re.sub(r"\s+", " ", caps[0] if isinstance(caps[0], str) else str(caps[0]))
        print("  %-11s log=%3d B %-40r screen-tail=%r"
              % (lab, len(blob), blob[:40], screen[-40:]))
        os.unlink(log.name)
        sys.stdout.flush()
