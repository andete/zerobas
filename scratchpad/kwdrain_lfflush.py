#!/usr/bin/env python3
"""docs/spec-basic-lfiles.md §3.3 records a CHOICE: *"LPTPOS is not maintained by
LFILES ... Every LFILES entry ends with CR/LF, so the head is at column 0 when
the statement ends and the R-LP16 flush at command level is a no-op either way.
No row measures it."*

The premise is true and the conclusion does not follow: the head is at column 0
when the statement ends only if nothing PARKED it mid-line first. Park it, and
R-LP16 fires on zerobas (LPTPOS still reads 2) and does not on the CF-3300 --
two extra bytes in the printer stream.

Three arms, one boot each so every log is its own (batched, the log accumulates):
  lf.mid   head parked at 2, then LFILES      -- the subject
  lf.rest  head at 0, then LFILES             -- the case the spec reasoned about
  ctl.mid  head parked at 2, no LFILES        -- what R-LP16 alone does
"""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [
    ("lf.mid",  ['10 LPRINT"AB";', '20 LFILES', '30 PRINT"[P";LPOS(0);"]"', 'RUN']),
    ("lf.rest", ['10 LFILES', '20 PRINT"[P";LPOS(0);"]"', 'RUN']),
    ("ctl.mid", ['10 LPRINT"AB";', '20 PRINT"[P";LPOS(0);"]"', 'RUN']),
]
for name in (sys.argv[1:] or ["zb", "cf3300"]):
    cfg = probe_sides.sides(name)[name]
    print("=== %s (%s)" % (name, cfg["machine"]))
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
        print("  %-8s LPOS=%-5s log=%3d B  tail=%r" % (lab, m[-1] if m else "NONE",
                                                       len(blob), blob[-14:]))
        os.unlink(log.name)
        sys.stdout.flush()
