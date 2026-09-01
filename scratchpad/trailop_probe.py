#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TRAILOP — a trailing binary operator, in seven contexts.

Closes the 🙋 item that asked whether ~18 B was worth spending to make `5+`
read ERR 2. It is not, because after D-MISSOPBOUND there is nothing left to
fix: 0 DIFF on all seven shapes.

🎯 THE ANSWER DEPENDS ENTIRELY ON WHAT FOLLOWS THE OPERATOR, which the filed
row did not record. `X=(5+)`, `IF 5+ THEN` and `ABS(5+)` have a token after
the empty slot and are ERR 2 on all three; `X=5+` and `PRINT 5+` end the
statement there and are ERR 24 on all three. Filing a divergence without the
WHOLE typed line makes it unreproducible
[[a-justification-parenthesis-is-an-unrun-claim]].
"""
import os, sys
sys.path.insert(0, os.path.join("probes","basic"))
import basic_probe_deffn as D
CASES, ORDER = {}, []
def add(l, setup, expr='X'):
    CASES[l]=(setup,expr); ORDER.append(l)
add('a.print',  ['X=99','PRINT 5+'])
add('b.paren',  ['X=99','X=(5+)'])
add('c.chain',  ['X=99','X=5+:PRINT 1'])
add('d.assign', ['X=99','X=5+'])
add('e.if',     ['X=99','IF 5+ THEN Z=1'])
add('f.arg',    ['X=99','X=ABS(5+)'])
add('g.two',    ['X=99','X=5+6+'])
D.CASES.update(CASES)
sides="vg8020,cf3300,zb".split(",")
res={s: D.run_side(s,ORDER) for s in sides}
w=max(len(l) for l in ORDER)
print(f"{'row':<{w}}  {'typed':<18}  " + "  ".join(f"{s:>14}" for s in sides))
for l in ORDER:
    cells=[str(res[s].get(l)) for s in sides]
    tag = "" if len(set(cells))==1 else "   DIFF"
    print(f"{l:<{w}}  {CASES[l][0][-1]:<18}  " + "  ".join(f"{c:>14}" for c in cells) + tag)
