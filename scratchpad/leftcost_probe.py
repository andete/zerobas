#!/usr/bin/env python3
r"""D-POOLCAP round 3: what does LEFT$(s,n) COST -- n bytes, or len(s)?

Round 2 bisected the failing expression term by term. The concat chain is
identical on all three sides (LEN 3 / 23 / 43, and LEN(X$+X$)=40), and the very
first row that diverges is the one that wraps it in `LEFT$(...,0)` -- asking for
ZERO characters. `FRE("")` is exonerated: `LEFT$(X$+X$,0)+A$` has no FRE in it
and fails too.

HYPOTHESIS: zerobas allocates len(SOURCE) for a LEFT$ result instead of the
requested length, so `LEFT$(<43 B temp>,0)` needs 43 more bytes on top of the
43 already held -- 86 against the 76 free -- while the references allocate 0.

This measures the cost DIRECTLY instead of inferring it from a failure: at a pool
big enough that nothing fails, read FRE("") before and after a single store, so
the drop IS the price. RIGHT$/MID$ are included because a per-verb answer and a
shared-helper answer look different here, and only the row set can say which.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

BIG = 'X$="ABCDEFGHIJ"+"KLMNOPQRST"'          # a 20-char heap string
SETUP = ['CLEAR 400', BIG]
NEW = {
    'p.base':    (SETUP,                       'FRE("")'),
    'p.left0':   (SETUP + ['Y$=LEFT$(X$,0)'],  'FRE("")'),
    'p.left5':   (SETUP + ['Y$=LEFT$(X$,5)'],  'FRE("")'),
    'p.left20':  (SETUP + ['Y$=LEFT$(X$,20)'], 'FRE("")'),
    'p.right0':  (SETUP + ['Y$=RIGHT$(X$,0)'], 'FRE("")'),
    'p.mid0':    (SETUP + ['Y$=MID$(X$,1,0)'], 'FRE("")'),
    'p.plain':   (SETUP + ['Y$=X$'],           'FRE("")'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>12}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>12}" for s in sides))
print("\ncost = p.base - row  (bytes the single store charged the pool)")
for s in sides:
    try:
        base = int(res[s].get('p.base'))
    except (TypeError, ValueError):
        print(f"  {s}: no base reading"); continue
    for l in labels:
        if l == 'p.base':
            continue
        try:
            print(f"  {s:<8} {l:<10} charged {base - int(res[s].get(l)):>4} B")
        except (TypeError, ValueError):
            print(f"  {s:<8} {l:<10} {res[s].get(l)!r}")
