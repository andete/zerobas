#!/usr/bin/env python3
"""D-KWDRAIN round A after the disk slice: the words whose filed blocker is a
CONSTANT or a MODE, re-verified before being believed.

  * `USR` — "machine code to call". One POKEd $C9 (RET) IS machine code.
  * `SCREEN` — filed as "its only discriminating value is a MODE CHANGE, and
    SCREEN 1 is 32 columns while this capture parses a 40-column screen". You
    never have to STAY in the mode: read SCRMOD and come back.
  * `KEY` — filed as blocked because FNKSTR is not in basic/sysvars.inc.
    `KEY LIST` prints the definitions to the screen, which needs no constant.
  * the `WAIT` port values, MEASURED ONLY -- no WAIT is executed here. A mask
    that is never satisfied blocks for ever and would take the whole batch with
    it, so the port has to be proved non-zero BEFORE a row exists.

Each subject is paired with its BLIND SHAPE: the same readback with the verb
removed, or with an undefined name in its place.
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides

CASES = [
    ("usr",       'POKE-8192,&HC9:DEFUSR=-8192:A=USR(7):PRINT"[X";A;"]"'),
    ("usr.stub",  'POKE-8192,&HC9:A=ZZQ(7):PRINT"[X";A;"]"'),
    ("scrmod.0",  'A=PEEK(&HFCAF):PRINT"[X";A;"]"'),
    ("scrmod.2",  'SCREEN2:A=PEEK(&HFCAF):SCREEN0:PRINT"[X";A;"]"'),
    ("inp.a8",    'PRINT"[X";INP(&HA8);"]"'),
    ("inp.a2",    'OUT&HA0,14:PRINT"[X";INP(&HA2);"]"'),
    ("inp.a9",    'PRINT"[X";INP(&HA9);"]"'),
    ("key.list",  'KEY LIST'),
    ("key.set",   'KEY 1,"ZZQ":KEY LIST'),
]

for name in (sys.argv[1:] or ["zb"]):
    cfg = probe_sides.sides(name)[name]
    specs = [("stored", omsx_repl.as_stored(l)) for _, l in CASES]
    caps = omsx_repl.run_cases(cfg["machine"], specs, batch=True,
                               reset=cfg["reset"] + ("NEW", "CLS"),
                               boot=cfg["boot"], step=3.5, cap_gap=12.0,
                               timeout=900.0)
    print("=== %s (%s)" % (name, cfg["machine"]))
    for (tag, l), cap in zip(CASES, caps):
        if tag.startswith("key"):
            rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
            print("  --- %s" % tag)
            for i, r in enumerate(rows):
                if r.strip():
                    print("      %2d |%s|" % (i, r))
            continue
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        m = re.findall(r"\[X\s*(-?\d+)\s*\]", txt)
        print("  %-10s %-6s | %s" % (tag, m[-1] if m else "NONE", txt[-90:]))
    sys.stdout.flush()
