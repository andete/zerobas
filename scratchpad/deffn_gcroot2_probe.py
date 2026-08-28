#!/usr/bin/env python3
r"""D-FNGCROOT round 2: allocate AFTER the collection, before reading the formal.

Round 1 was green on all three sides and it was green for the WRONG REASON.
The mechanism, read out of the code and then confirmed by measurement:

  * `str_set_key` (basic/vars.asm:979) snapshots the actual into a TEMP, stores
    that copy's descriptor into the destination, and then RESTORES TEMPTOP --
    releasing the temp. The destination, while an FN call is live, is the shadow
    slot (`scv_find` consults `fn_shadow_find` first). So the formal's body is a
    COPY referenced ONLY by a slot `sg_walk` never visits.
  * But compaction moves live bodies UPWARD -- measured, 47851 -> 47868 in
    scratchpad/deffn_gcmove_probe.py. The dead copy is the LOWEST allocation, so
    a collection alone moves everything AWAY from it and leaves its bytes intact.

So round 1's `FRE("")` could never have caught this. The frontier has to march
back DOWN over the copy, which means ALLOCATING after the collection and before
the formal is read -- all inside one expression, left to right:

    DEF FNA$(S$)=LEFT$(STR$(FRE(""))+X$+X$,0)+S$
                       \____ GC ____/  \_ alloc _/   then read the stale slot
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

HOLE = 'B$="12345"+"67890":A$="AB"+"CD":B$=""'
BIG  = 'X$="ABCDEFGHIJ"+"KLMNOPQRST"'
NEW = {
    # SUBJECT: collect, then allocate over the dead copy, then read the formal
    'g2.sub':  (['CLEAR 400', HOLE, BIG,
                 'DEF FNA$(S$)=LEFT$(STR$(FRE(""))+X$+X$,0)+S$'], 'FNA$(A$)'),
    # CONTROL A: identical body, ordinary VARIABLE instead of the formal.
    # A$ is a walked scalar, so it must survive -- isolates the shadow slot.
    'g2.ctlv': (['CLEAR 400', HOLE, BIG], 'LEFT$(STR$(FRE(""))+X$+X$,0)+A$'),
    # CONTROL B: the same formal read with NO collection and NO allocation
    'g2.ctln': (['CLEAR 400', HOLE, BIG,
                 'DEF FNB$(S$)=LEFT$(X$,0)+S$'], 'FNB$(A$)'),
    # CONTROL C: allocation but no collection -- separates "GC moved it" from
    # "the allocator marched over it"
    'g2.ctla': (['CLEAR 400', HOLE, BIG,
                 'DEF FNC$(S$)=LEFT$(X$+X$,0)+S$'], 'FNC$(A$)'),
}
for n in (100, 150, 200, 300):
    NEW['g2.cap%d' % n] = (['CLEAR %d' % n, HOLE, BIG],
                           'LEFT$(STR$(FRE(""))+X$+X$,0)+A$')
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>18}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>18}" for s in sides))
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
