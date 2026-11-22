#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""strtms-acceptance row `long` went red with D-TRGFLGISR part 2 (MUSICF 7 where the VG-8020 has 1). How long does
the over-long PLAY take, and what are MUSICF / PLYCNT / the voice queues' GET / PUT right after it? Black box: TIME
before and after, PEEKs of the published cells. No ROM byte is read.
    python3 -u scratchpad/playlong_probe.py > scratchpad/PLAYLONG_run1.out
    python3 -u scratchpad/playlong_probe.py direct ...   (the gate row's form: one direct statement)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides  # noqa: E402
P = ["10 T=TIME:PLAY \"T255L64CDEFGABCDEFGABCDEFGABCDEFGABCDEFGABCDEFGAB\":U=TIME:A=PEEK(&HFB40):B=PEEK(&HFB3F)",
     "20 Q$=\"\":FOR I=0 TO 17:Q$=Q$+RIGHT$(\"0\"+HEX$(PEEK(&HF959+I)),2):NEXT",
     "30 PRINT \"[\";U-T;A;B;Q$;\"]\"", "RUN"]
D = ['T=TIME:PLAY "T255L64CDEFGABCDEFGABCDEFGABCDEFGABCDEFGABCDEFGAB":U=TIME:A=PEEK(&HFB40):B=PEEK(&HFB3F):'
     'PRINT "[";U-T;A;B;"]"']
if "direct" in sys.argv[1:]:
    P = D
    sys.argv.remove("direct")
for side in sys.argv[1:] or ("vg8020", "zb"):
    m = probe_sides.MACHINES[side]
    for k in range(2):
        scr = omsx_repl.run_batch(m["machine"], [("direct", P)], boot=m["boot"], reset=m["reset"])[0] or ""
        v = re.findall(r"\[([^\]]*)\]", scr)
        print(f"{side:7} {k}: {v[-1] if v else '<none>'}")
