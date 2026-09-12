#!/usr/bin/env python3
"""D-KWDRAIN, the tape and printer-log clusters: RE-VERIFY the blockers.

`CLOAD`/`CSAVE` were filed as needing "a tape rig", and one exists
(`cassetteplayer new` + probes/lib/cas_decode.py). But the rig RECORDS; nothing
in this tree ever PLAYS a tape, so the two verbs are not one blocker:

  * `CSAVE` writes, and a write has a SCREEN-VISIBLE consequence nobody has
    used -- it takes REAL TIME. A cassette leader plus a two-line program is
    seconds of emulated time, and `TIME` counts them. A CSAVE that parsed and
    did nothing returns instantly.
  * `CLOAD` needs a tape that already HOLDS a program, i.e. a playable fixture
    (`cassetteplayer insert`), which appears NOWHERE in this tree.

`LLIST`/`LFILES` were filed as needing a reader for the printer LOG. Maybe not:
both END THEIR OUTPUT WITH A NEWLINE, so they drive the printer head back to
column 0 -- and `LPOS` returns that to the SCREEN. Park the head mid-line first
and the readback moves: 2 if the verb did nothing, 0 if it printed anything.

Every arm here is paired with the blind shape it has to beat.
"""
import os, re, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")

TAPE = [
    ("csave",     'A=1:T=TIME:CSAVE"X":PRINT"[T";TIME-T>100;"]"'),
    ("csave.ctl", 'A=1:T=TIME:PRINT"[T";TIME-T>100;"]"'),
    ("csave.raw", 'A=1:T=TIME:CSAVE"X":PRINT"[T";TIME-T;"]"'),
]
PRN = [
    ("llist",     'LPRINT"AB";:LLIST:PRINT"[P";LPOS(0);"]"'),
    ("llist.ctl", 'LPRINT"AB";:PRINT"[P";LPOS(0);"]"'),
    ("lfiles",    'LPRINT"AB";:LFILES:PRINT"[P";LPOS(0);"]"'),
]

def show(rows, caps, tag):
    for (lab, line), cap in zip(rows, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        after = txt.split("RUN", 1)[1] if "RUN" in txt else txt   # never the echo
        m = re.findall(r"\[[TP]\s*(-?\d+)\s*\]", after)
        print("  %-10s %-7s | %s" % (lab, m[-1] if m else "NONE", after[:70]))

for name in (sys.argv[1:] or ["zb"]):
    cfg = probe_sides.sides(name)[name]
    wav = os.path.join(tempfile.mkdtemp(prefix="zb_kwtape_"), "t.wav")
    specs = [("stored", omsx_repl.as_stored(l)) for _, l in TAPE]
    caps = omsx_repl.run_cases(cfg["machine"], specs, batch=True,
                               reset=cfg["reset"] + ("NEW", "CLS"),
                               boot=cfg["boot"], step=5.0, cap_gap=30.0,
                               timeout=900.0,
                               prologue=(f"cassetteplayer new {{{wav}}}",))
    print("=== %s  TAPE" % name)
    show(TAPE, caps, "T")
    print("      recorded WAV: %d bytes"
          % (os.path.getsize(wav) if os.path.exists(wav) else -1))

    log = tempfile.NamedTemporaryFile(suffix=".prn", delete=False); log.close()
    kw = {}
    img = probe_sides.diska(name, TEST_DSK)
    if img:
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False); tmp.close()
        shutil.copy(TEST_DSK, tmp.name); kw["diska"] = tmp.name
    specs = [("stored", omsx_repl.as_stored(l)) for _, l in PRN]
    caps = omsx_repl.run_cases(cfg["machine"], specs, batch=True,
                               reset=cfg["reset"] + ("NEW", "CLS"),
                               boot=cfg["boot"], step=5.0, cap_gap=20.0,
                               timeout=900.0,
                               prologue=(f"set printerlogfilename {{{log.name}}}",
                                         "plug printerport logger"), **kw)
    print("=== %s  PRINTER (disk=%s)" % (name, "yes" if img else "no"))
    show(PRN, caps, "P")
    print("      printer log: %d bytes" % os.path.getsize(log.name))
    os.unlink(log.name)
    sys.stdout.flush()
