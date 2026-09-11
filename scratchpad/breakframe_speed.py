#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""D-BRKFRAME: what did removing the per-statement BREAKX actually buy?
TIME is JIFFY, so the answer is in frames. Longer loops than the 400-iteration
first cut, whose 99-vs-98 result was inside its own +/-1 frame resolution."""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides

CASES = [("empty", "FOR I=1 TO 4000:NEXT"),
         ("assign", "FOR I=1 TO 2000:X=I:NEXT"),
         ("add", "FOR I=1 TO 2000:X=I+1:NEXT"),
         ("goto", "FOR I=1 TO 2000:GOSUB 100:NEXT")]
TAIL = ['100 RETURN']

def face(c, tag):
    c = c or ""; i = c.rfind("[" + tag)
    if i < 0: return None
    j = c.find("]", i)
    return " ".join(c[i + len(tag) + 1:j].split()) if j > 0 else None

side = sys.argv[1] if len(sys.argv) > 1 else "zb"
cfg = probe_sides.sides(side)[side]
for tag, body in CASES:
    lines = [f'10 A=TIME:{body}:B=TIME', f'20 PRINT"[{tag} ";B-A;"]"'] + TAIL + ['RUN']
    cap = omsx_repl.run_cases(cfg["machine"], [(tag, lines)], batch=False,
                              boot=cfg["boot"], reset=cfg["reset"], run_gap=45.0)[0]
    print(f"  {side:8} {tag:8} {face(cap, tag)} frames")
