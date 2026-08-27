#!/usr/bin/env python3
"""Settle EVERY address basic_probe_clear.py hardcodes, on the reference machine.

Two of its six (FRETOP $F691, STREND $F693) read $0000 on a real MSX -- dead
cells -- and Case 3 reported them SAME/SAME.  STKTOP $FC4C reads $0000 too.
Rather than fix the two I happened to look at, read the whole neighbourhood and
let the machine say which cells are live.

DISCRIMINATOR: a live pointer holds a plausible RAM address AND tracks the
argument that should move it.  CLEAR 200,&HD000 vs CLEAR 200,&HC000 moves the
memory ceiling, so HIMEM/STKTOP/FRETOP-family cells must follow it.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_clear as C

CAND = [0xF672, 0xF674, 0xF676, 0xF691, 0xF693, 0xF69B,
        0xF6C2, 0xF6C4, 0xF6C6, 0xFC48, 0xFC4A, 0xFC4C, 0xFC4E]

def snap(stmt):
    return C.run(C.REF_MACHINE, None, C.lines_for(stmt), [(a, 2) for a in CAND])

hi = snap("CLEAR 200,&HD000")
lo = snap("CLEAR 200,&HC000")
print("  addr     D000-ceiling   C000-ceiling   verdict")
for a in CAND:
    ra, rb = C.get(hi, a) or "----", C.get(lo, a) or "----"
    def le(h):
        try: return int(h[2:4] + h[0:2], 16)
        except Exception: return None
    va, vb = le(ra), le(rb)
    if va == 0 and vb == 0:
        v = "DEAD ($0000 both)"
    elif ra != rb:
        v = f"TRACKS THE CEILING  ${va:04X} -> ${vb:04X}  ({vb-va:+d})"
    else:
        v = f"live, ceiling-independent  ${va:04X}"
    print(f"  ${a:04X}   {ra:>12}   {rb:>12}   {v}")
