#!/usr/bin/env python3
r"""D-NGRAM14 — one `fac_dbl_int16` for the four "FAC holds a double, publish it"
tails: the sub-ROM math dispatch, EXP(-huge), round_and_finalize, and `^`.

ONE ROW PER REACHER, because the collapse's whole claim is that four different
callers arrive at one tail and leave through their OWN caller. A row set that
exercised only the dispatch would say nothing about the other three.

  r.sqr / r.atn / r.log / r.exp   evmc_dispatch (basic/expr.asm) -- four verbs
                                  through the one sub-ROM dispatch site
  r.exphuge                       evmc_exp_huge: EXP of a large NEGATIVE is 0,
                                  not an error, and it reaches the tail by its
                                  own `jp`
  r.pow                           `^` (basic/float-arith.asm)
  r.round                         round_and_finalize, the FALLTHROUGH reacher --
                                  plain float arithmetic, no sub-ROM verb at all
  ctl.int / ctl.str               🟢 CONTROLS: integer arithmetic and a string
                                  op, which reach none of the four
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D                                    # noqa: E402

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

add('r.sqr',     [], 'SQR(9)')
add('r.atn',     [], 'ATN(1)')
add('r.log',     [], 'LOG(1)')
add('r.exp',     [], 'EXP(0)')
# EXP(-huge) -> 0 on both references; the arm that is NOT an error.
add('r.exphuge', [], 'EXP(-1E38)')
# 📌 THE DOMAIN OF THE `evmc_exp_huge` REACHER, because its own comment makes a
# claim -- "EXP(-huge) -> 0, not an error" -- that `r.exphuge` REFUTES: both
# references answer Overflow. These rows say whether that is true of every
# large negative or only of the extreme ones, which is what a fix would need.
add('x.m100',    [], 'EXP(-100)')
add('x.m200',    [], 'EXP(-200)')
add('x.m1e30',   [], 'EXP(-1E30)')
# 🔴 WHERE EACH MACHINE SWITCHES from a value to the error. A fix that makes
# underflow an ERROR is only right if the BOUNDARY agrees too -- otherwise it
# just moves the divergence to a different argument.
add('x.m150',    [], 'EXP(-150)')
add('x.m170',    [], 'EXP(-175)')
add('x.m180',    [], 'EXP(-180)')
add('x.p100',    [], 'EXP(100)')
add('x.p1e30',   [], 'EXP(1E30)')
add('r.pow',     [], '2^10')
# round_and_finalize: reached by FALLTHROUGH, and by ordinary float arithmetic
# rather than by any named verb -- the reacher a verb-shaped row set would miss.
add('r.round',   [], '1.5*3')
add('r.round2',  [], '1/3')
# 🟢 CONTROLS. Integer arithmetic publishes through a different path entirely,
# and a string op touches none of it. If a knife to the shared tail moves these,
# the apparatus broke, not the tail.
add('ctl.int',   [], '3+4')
add('ctl.str',   [], '"AB"+"CD"')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides) + "   verdict")
diff, blind = [], []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if refs and not same:
        diff.append(l)
    if any("<NO OUTPUT>" in str(res[s].get(l)) or "<NO CAPTURE>" in str(res[s].get(l))
           for s in sides):
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}"
      + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
raise SystemExit(1 if diff else 0)
