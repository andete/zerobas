#!/usr/bin/env python3
r"""D-DUPSUPPLY: the pu_ifc path still raises ERR 5 after the alias collapse.

`pu_ifc` was a ninth byte-identical copy of `gb_illegal`'s `ld a,5 / jp
raise_error`; it is now `pu_ifc equ gb_illegal` (+5 B of main page 1). NOTHING in
`make gates` names PRINT USING, so the collapsed path needs its own reading. The
D-PUSING measurements it implements: `PRINT USING"abc"` is ERR 2, and
`PRINT USING"abc";` / `PRINT USING"abc";5` are ERR 5 -- the pu_ifc arm.

The statement goes in a SETUP line, so the fixture's `ON ERROR GOTO 900` traps it
and the row reads `[ERR n AT 20]`. `u.ok` is the control: a format WITH a field
must still print, or the collapse broke the verb rather than the error tail.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

NEW = {
    'u.nofld':   (['PRINT USING"abc"'],    '"X"'),
    'u.nofldsc': (['PRINT USING"abc";'],   '"X"'),
    'u.nofldv':  (['PRINT USING"abc";5'],  '"X"'),
    'u.ok':      (['PRINT USING"##";5'],   '"X"'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides))
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
