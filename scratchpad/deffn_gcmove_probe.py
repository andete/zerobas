#!/usr/bin/env python3
"""Does the compaction actually MOVE the subject string? The arm the first cut lacked.

deffn_gcroot_probe.py's four rows all agreed at ABCD -- and its "does it move"
arm was BLIND: `VARPTR(A$)` is the address of the DESCRIPTOR, which lives in the
variable table and does not move during a collection at all. It reported an
identical number on all three sides and proved nothing.

🔴 A CASE THAT AGREES CAN AGREE FOR THE WRONG REASON. If the body never
relocates, a shadow slot that is not a GC root still reads correctly, and the
green row says nothing about the hazard. So read the descriptor's PTR FIELD
either side of `FRE("")` and require it to CHANGE.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

PTR = 'PEEK(V+1)+256*PEEK(V+2)'
NEW = {
    # the ptr field before vs after a compaction, same run
    'm.move':  (['CLEAR 200', 'B$="12345"+"67890":A$="AB"+"CD":B$=""',
                 'V=VARPTR(A$):P=%s' % PTR, 'Q=FRE("")'],
                'P;%s' % PTR),
    # a bigger hole: three junk bodies dropped below the subject
    'm.move2': (['CLEAR 400',
                 'C$="AAAAA"+"BBBBB":D$="CCCCC"+"DDDDD":A$="AB"+"CD"',
                 'C$="":D$="":V=VARPTR(A$):P=%s' % PTR, 'Q=FRE("")'],
                'P;%s' % PTR),
    # what VARPTR itself reports before/after -- the arm that was blind, kept
    # as an explicit NEGATIVE control so the blindness is on the record
    'm.varptr': (['CLEAR 200', 'B$="12345"+"67890":A$="AB"+"CD":B$=""',
                  'V=VARPTR(A$)', 'Q=FRE("")'],
                 'V;VARPTR(A$)'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides))
print("\n(each cell is `before after`; MOVED means the two differ)")
for l in labels:
    for s in sides:
        f = str(res[s].get(l) or "")
        parts = f.split()
        if len(parts) == 2:
            print(f"  {l:<9} {s:<8} {'MOVED' if parts[0] != parts[1] else 'did NOT move'}"
                  f"  ({parts[0]} -> {parts[1]})")
