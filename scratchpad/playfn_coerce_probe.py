#!/usr/bin/env python3
r"""D-PLAYFN round 3: does PLAY(n) TRUNCATE its argument, or ROUND it?

Round 2 settled the semantics -- PLAY(0) is "any voice", PLAY(1..3) are the three
voices, 4 and -1 are ERR 5 -- and left the coercion open. Two readings survive it:

    PLAY(1.7) = -1 with voice 1 playing   truncate -> 1 -> -1  ✅
                                          round    -> 2 ->  0  ✗
    PLAY(0.9) = -1                        truncate -> 0 -> -1  ✅
                                          round    -> 1 -> -1  ✅   (separates nothing)

One row pointing at truncation is one row. These separate the two properly, with
voice 3 playing so the answers differ in BOTH directions:

    PLAY(2.7)   truncate -> 2 ->  0        round -> 3 -> -1
    PLAY(3.4)   truncate -> 3 -> -1        round -> 3 -> -1     (agrees; kept as a control)
    PLAY(3.7)   truncate -> 3 -> -1        round -> 4 -> ERR 5

The last is the sharpest: rounding takes it OUT OF DOMAIN, so the two rules give
an answer and an error, not two answers.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

V3 = 'PLAY "","","L1CDEFGAB"'
NEW = {
    'c.2_7':  ([V3], 'PLAY(2.7)'),
    'c.3_4':  ([V3], 'PLAY(3.4)'),
    'c.3_7':  ([V3], 'PLAY(3.7)'),
    'c.neg0': ([V3], 'PLAY(-0.4)'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>18}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>18}" for s in sides))
print("""
verdict key (voice 3 is the one playing):
  c.2_7  -1 => ROUND     0 => TRUNCATE
  c.3_7  -1 => TRUNCATE  ERR 5 => ROUND""")
