#!/usr/bin/env python3
r"""D-PLAYFN scout: the PLAY(n) FUNCTION -- claim re-run, then its domain mapped.

TODO.md (filed 2026-08-24 by scratchpad/seam_classify.py): `P=PLAY(0)` answers -1
(playing) / 0 (idle) on both references and raises `Missing operand` on zerobas --
the function form is unparsed. Separate surface from the PLAY STATEMENT.

Re-run the claim before building on it, and map what the references actually DO,
because the fix has to reproduce the semantics, not just stop erroring:

  idle vs during   -- the two states the function reports
  n = 0,1,2,3      -- MSX documents 0 as "any voice" and 1..3 as one each, but
                      that is a claim to MEASURE, not to inherit
  n = 4, -1        -- the domain edge: which error, and is it raised at all
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

LONG = 'PLAY"L1CDEFGAB"'          # queued in the background; still sounding at line 60
NEW = {
    'q.idle0':   ([], 'PLAY(0)'),
    'q.idle1':   ([], 'PLAY(1)'),
    'q.idle23':  ([], 'PLAY(2);PLAY(3)'),
    'q.during0': ([LONG], 'PLAY(0)'),
    'q.during1': ([LONG], 'PLAY(1)'),
    'q.during23':([LONG], 'PLAY(2);PLAY(3)'),
    'q.n4':      ([], 'PLAY(4)'),
    'q.nneg':    ([], 'PLAY(-1)'),
    # the STATEMENT surface still works -- a control, so a PLAY fixture fault
    # reddens something before it reddens the function rows
    'q.stmt':    ([LONG], '"OK"'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>24}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>24}" for s in sides))
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
