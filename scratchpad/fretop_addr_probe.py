#!/usr/bin/env python3
"""Which address IS the published FRETOP/STREND?  Ask the reference machine.

basic_probe_clear.py hardcodes FRETOP $F691 and STREND $F693.  $F691 appears
NOWHERE else in the tree; basic/sysvars.inc:918 states the published chain as
TXTTAB $F676 <= VARTAB $F6C2 <= ARYTAB $F6C4 <= STREND $F6C6 -- which
contradicts $F693 outright.  So read the whole neighbourhood on a real MSX and
let the machine say which cells behave like heap pointers.

A published heap pointer must (a) hold a plausible RAM address and (b) MOVE when
CLEAR is given a different string-space size.  A cell that does neither is not it.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_clear as C

CAND = [0xF691, 0xF693, 0xF69B, 0xF6C2, 0xF6C4, 0xF6C6, 0xF676]

def snap(stmt):
    return C.run(C.REF_MACHINE, None, C.lines_for(stmt), [(a, 2) for a in CAND])

a = snap("CLEAR 200,&HD000")
b = snap("CLEAR 1000,&HD000")
print(f"{'addr':>7}  {'CLEAR 200':>10}  {'CLEAR 1000':>10}   moved?")
for addr in CAND:
    ra, rb = C.get(a, addr), C.get(b, addr)
    def le(h):
        try: return int(h[2:4] + h[0:2], 16)
        except Exception: return None
    va, vb = le(ra or ""), le(rb or "")
    moved = "MOVED" if (ra != rb) else "same"
    d = f"  delta={vb-va:+d}" if (va is not None and vb is not None and va != vb) else ""
    print(f"  ${addr:04X}  {ra!s:>10}  {rb!s:>10}   {moved}{d}"
          f"   (${va:04X} -> ${vb:04X})" if va is not None and vb is not None else
          f"  ${addr:04X}  {ra!s:>10}  {rb!s:>10}   {moved}")
