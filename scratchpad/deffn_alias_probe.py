#!/usr/bin/env python3
"""D-FNALIAS scout: does binding formal 0 shadow the caller for actual 1?

TODO.md (D-DEFFN, docs/deffn-impl-2026-08-22.md §8) filed this against the DRAFT:
"the draft binds in place ... writes slot 0 before the second actual reads it",
with the reference's behaviour UNMEASURED. DEF FN has SHIPPED since (D-DEFFNLAND,
2026-08-23), so the premise is re-run here rather than inherited.

THE SEPARATOR. `DEF FNA(P,Q)=P*100+Q` with a caller variable also called P:

    P=3 : PRINT FNA(5,P)
        503  -> every actual is evaluated in the CALLER's scope
        505  -> binding P:=5 already shadows the caller when Q's actual is read

and the nested form the item actually describes -- a callee formal sharing a name
with the CALLER's formal:

    DEF FNA(X,Q)=X*100+Q : DEF FNB(X)=FNA(9,X) : PRINT FNB(3)
        903  -> caller's frame still visible
        909  -> callee's slot 0 shadows it

Each has a POSITIVE CONTROL with no shared name, so a broken two-formal fixture
reddens the control before it reddens the subject.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

NEW = {
    'o.alias':          (['DEF FNA(P,Q)=P*100+Q', 'P=3'],            'FNA(5,P)'),
    'o.alias.ctl':      (['DEF FNA(P,Q)=P*100+Q'],                   'FNA(5,7)'),
    'o.aliasnest':      (['DEF FNA(X,Q)=X*100+Q', 'DEF FNB(X)=FNA(9,X)'], 'FNB(3)'),
    'o.aliasnest.ctl':  (['DEF FNA(X,Q)=X*100+Q', 'DEF FNB(X)=FNA(9,7)'], 'FNB(3)'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")

res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>12}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>12}" for s in sides))
print()
for l in labels:
    vals = {s: res[s].get(l) for s in sides}
    refs = {s: v for s, v in vals.items() if s != "zb"}
    if len(set(refs.values())) > 1:
        print(f"  {l}: THE REFERENCES DISAGREE {refs} -- no oracle")
    elif "zb" in vals and refs and vals["zb"] not in set(refs.values()):
        print(f"  {l}: DIVERGENCE  zb={vals['zb']!r}  ref={list(refs.values())[0]!r}")
    elif refs:
        print(f"  {l}: agree ({list(refs.values())[0]!r})")

# --- D-FACEPIN: the FACE, not just the row label ----------------------------
# 🔴 A FILED FACE ROTS WITHOUT THE ROW CEASING TO DIVERGE, AND NOTHING DETECTS
# THAT. `filed_row_sweep` adjudicates a divergent row as known / unfiled / no
# longer diverging -- so a row that still diverges but to a DIFFERENT face is
# `known`, and reads green. TODO.md records five instances, each found by hand.
# 🎯 Same shape as `basic_probe_nodisk.PINNED` and D-DEFERPIN: pin the VALUES and
# go RED on drift in EITHER direction. ⚠️ Keyed by SIDE NAME, never by column
# position -- the side list is an argv option, so a positional pin would compare
# the wrong machine without saying so.
PINNED = {
    # measured 2026-09-10. The filing is "two formals of ONE call can alias";
    # the CONTROLS (o.alias.ctl 507, o.aliasnest.ctl 907) agree on all three and
    # are deliberately NOT pinned here -- they are the probe's own fixture check.
    "o.alias":     {"vg8020": "503", "cf3300": "503", "zb": "505"},
    "o.aliasnest": {"vg8020": "903", "cf3300": "903", "zb": "909"},
}

_drift = []
for _lbl, _want in PINNED.items():
    for _side, _face in _want.items():
        if _side not in res:
            continue                      # side not run; that is not a drift
        _got = str(res[_side].get(_lbl))
        if _got != _face:
            _drift.append(f"{_lbl}[{_side}]: pinned {_face!r}, measured {_got!r}")
if _drift:
    print("\n\U0001f534 PINNED FACE DRIFT -- the row may still diverge, but NOT to "
          "the face this tree has filed:")
    for _d in _drift:
        print(f"     {_d}")
    print("  Re-read the owning entry before touching anything: either the "
          "behaviour moved, or the filing was wrong when it was written.")
    raise SystemExit(2)
