#!/usr/bin/env python3
"""D-FNGCROOT scout: is a STRING formal's shadow slot a GC root?

TODO.md (D-DEFFN, docs/deffn-impl-2026-08-22.md §8): the slot holds a [len][ptr]
descriptor, and `sg_walk` (sub/strheap.asm:750) visits scalars, arrays and temps
-- NOT the FN shadow area. Re-verified on the SHIPPED code, not the draft it was
filed against. "The ROW that would catch it does not exist yet." This builds it.

THE TRIGGER: `FRE("")` compacts before reporting (sub/strheap.asm:1446, measured
against the reference). Put it FIRST in the body so the collection happens BEFORE
the formal is read:

    DEF FNA$(S$)=LEFT$(STR$(FRE("")),0)+S$

`+` evaluates left to right, so the heap is compacted and only then is S$ fetched
from the shadow slot. If that slot was not walked, its ptr now aims at where the
body USED to be.

THE HEAP MUST ACTUALLY MOVE, or the row proves nothing: a string that does not
relocate is a case that agrees for the wrong reason. So a junk string is
allocated BELOW the subject and then dropped, leaving a hole for the compaction
to close. Every string is built by CONCATENATION -- a bare literal's descriptor
can point into the program text and never be a heap object at all.

THE CONTROL is the identical expression with an ordinary VARIABLE in place of the
formal. It exercises the same FRE, the same compaction and the same fixture, so a
GC fault or a fixture fault reddens it before it reddens the subject; only the
shadow slot separates them.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

HOLE = 'B$="12345"+"67890":A$="AB"+"CD":B$=""'
NEW = {
    # SUBJECT: the formal is read after a compaction
    'o.gcroot':      (['CLEAR 200', HOLE,
                       'DEF FNA$(S$)=LEFT$(STR$(FRE("")),0)+S$'], 'FNA$(A$)'),
    # CONTROL 1: same expression, ordinary variable -- no FN frame involved
    'o.gcroot.ctl':  (['CLEAR 200', HOLE], 'LEFT$(STR$(FRE("")),0)+A$'),
    # CONTROL 2: the same FN, called WITHOUT a compaction in front of the read
    'o.gcroot.ctl2': (['CLEAR 200', HOLE,
                       'DEF FNB$(S$)=LEFT$("",0)+S$'], 'FNB$(A$)'),
    # a heap string really does move across the collection (else the row is vacuous)
    'o.gcroot.move': (['CLEAR 200', HOLE], 'VARPTR(A$)'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>16}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>16}" for s in sides))
print()
for l in labels:
    v = {s: res[s].get(l) for s in sides}
    refs = {s: x for s, x in v.items() if s != "zb"}
    if len(set(refs.values())) > 1:
        print(f"  {l}: THE REFERENCES DISAGREE {refs} -- no oracle")
    elif "zb" in v and refs and v["zb"] not in set(refs.values()):
        print(f"  {l}: DIVERGENCE  zb={v['zb']!r}  ref={list(refs.values())[0]!r}")
    elif refs:
        print(f"  {l}: agree ({list(refs.values())[0]!r})")
