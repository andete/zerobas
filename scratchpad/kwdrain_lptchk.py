#!/usr/bin/env python3
"""`LPOS` and `LPRINT` were filed as needing "a reader for the PRINTER LOG (the
output never reaches the screen)". Re-verified: the READBACK does reach the
screen -- `LPOS(0)` is the printer head's COLUMN, and it moves when LPRINT puts
bytes on the head. What the log is needed for is the printed TEXT, which these
rows do not have to assert.

What IS needed is a PLUGGED printer: with nothing on the port the LSTOUT hazard
is a hang, so the plug is a `prologue`, the same seam basic_probe_lptverb.py
uses. Arms: the head at rest, the head after 3 bytes, and the same pair with no
printer plugged -- because if the unplugged machine answers identically, the
prologue is not doing anything and the row would be measuring nothing."""
import os, re, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
CASES = [
    ("lpos.rest", 'PRINT"[X";LPOS(0);"]"'),
    ("lpos.3",    'LPRINT"ABC";:PRINT"[X";LPOS(0);"]"'),
    ("lpos.7",    'LPRINT"ABCDEFG";:PRINT"[X";LPOS(0);"]"'),
]
for name in (sys.argv[1:] or ["zb"]):
    cfg = probe_sides.sides(name)[name]
    for plugged in (True, False):
        log = tempfile.NamedTemporaryFile(suffix=".prn", delete=False); log.close()
        plug = ((f"set printerlogfilename {{{log.name}}}", "plug printerport logger")
                if plugged else ())
        specs = [("stored", omsx_repl.as_stored(l)) for _, l in CASES]
        caps = omsx_repl.run_cases(cfg["machine"], specs, batch=True,
                                   reset=cfg["reset"] + ("NEW", "CLS"),
                                   boot=cfg["boot"], step=3.5, cap_gap=12.0,
                                   timeout=600.0, prologue=plug)
        print("=== %s  printer=%s" % (name, "PLUGGED" if plugged else "none"))
        for (tag, l), cap in zip(CASES, caps):
            txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
            # 🔴 the marker is in the ECHO too -- take what follows the RUN echo,
            # never a first/last match over the whole screen.
            after = txt.split("RUN", 1)[1] if "RUN" in txt else txt
            m = re.findall(r"\[X\s*(-?\d+)\s*\]", after)
            print("  %-10s %-6s | %s" % (tag, m[-1] if m else "NONE", after[:80]))
        os.unlink(log.name)
        sys.stdout.flush()
