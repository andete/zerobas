#!/usr/bin/env python3
r"""D-NGRAM10 — one `req_lineno` for RESUME / GOTO / GOSUB / ON ERROR GOTO.

All four open-coded the identical 7-instruction run: require the $0E line-number
token, raise ERR 2 without it, load BC from the LE pair and advance HL past the
operand. 10 B each, 40 B in all; an 11 B body plus four 3 B calls is 23 B.

🔴 BOTH HALVES, ONE ROW PER SITE. A row set covering only the success path would
leave `jp nz,stmt_error` -- half the run, and the half a `call` could break --
unwitnessed at every site.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- the SUCCESS half: BC = the line, HL past the operand, one row per site --
add('g.goto',   ['GOTO 60'],                                    '"jumped"')
add('g.gosub',  ['A=0', 'GOSUB 50', 'GOTO 60', 'A=7:RETURN'],   'A')
add('g.resume', ['ON ERROR GOTO 40', 'A=1/0', 'RESUME 60'],     '"resumed"')
# ⚠️ ex_on_error's success path is ALREADY on every row -- line 10 of the fixture
# is `ON ERROR GOTO 900`. This row is the RE-ARM, so the site has a witness that
# is about the site and not about the fixture.
add('g.onerr',  ['ON ERROR GOTO 900', 'A=1/0'],                 '"unreached"')

# --- the BAIL half (`jp nz,stmt_error`): a non-line-number operand -----------
add('b.goto',   ['GOTO A'],                                     '"unreached"')
add('b.gosub',  ['GOSUB A'],                                    '"unreached"')
# ⚠️ THESE TWO NEED THEIR OWN `CLS`, AND THAT IS THE ECHO FENCE, NOT A STYLE
# CHOICE. Their error fires at a SETUP line -- before the fixture's own CLS on
# line 60 -- so an UNTRAPPED message prints onto a screen that still holds the
# LIST echo of the typed program, and the capture reads the SOURCE TEXT back as
# the value. Measured: both references returned `";"unreached";"` here.
# [[trapsvc-echo-fence]]
add('b.onerr',  ['CLS', 'ON ERROR GOTO A'],                     '"bail-missed"')
add('b.resume', ['ON ERROR GOTO 40', 'A=1/0', 'CLS:RESUME A'],  '"bail-missed"')

# --- the neighbouring shapes the run must not have disturbed ----------------
add('n.goto0',  ['ON ERROR GOTO 0'],                            '"armed"')
add('n.gotoud', ['GOTO 12345'],                                 '"unreached"')
add('n.ifthen', ['IF 1 THEN 60'],                               '"then"')

# --- 🟢 controls ------------------------------------------------------------
add('ctl.num',  [], '1+1')
add('ctl.str',  ['B$="HI"'], 'B$')

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
    if not same: diff.append(l)
    # 🔴 THE BLINDNESS CHECK MUST READ EVERY SIDE, NOT JUST zb. `b.onerr` came
    # back DIFF with the REFERENCES echoing their own source text -- a run that
    # never reached its PRINT reads the TYPED LINE as a value -- while zb had a
    # clean reading. Checking only zb calls that a divergence.
    # [[readout-blind-to-its-own-subject]] [[trapsvc-echo-fence]]
    # 🔴 DETECT THE ECHO, NOT THE PAYLOAD. An earlier version blinded on the
    # word "unreached" -- but that word is also what a row PRINTS when the bail
    # fails to fire, so a real failure would have been filed as blindness. `;"`
    # is a fragment of the fixture's own PRINT statement and cannot occur in any
    # value. [[readout-blind-to-its-own-subject]]
    if any(any(m in str(res[s].get(l)) for m in
               ("<NO OUTPUT>", "<NO CAPTURE>", ';"'))
           for s in sides):
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}" + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
