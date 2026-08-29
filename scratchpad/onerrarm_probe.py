#!/usr/bin/env python3
r"""D-ONERRARM — WHEN does `ON ERROR GOTO` drop the handler it is replacing?

D-NGRAM10 found one row: `ON ERROR GOTO A` raises `Syntax error` UNTRAPPED on
both references and TRAPPED here. One row names a symptom; this asks where the
boundary is, by walking the statement's own parse in order.

  ex_on_error parses:   ERROR_TOKEN | GOTO_TOKEN | $0E lo hi | (resolve the line)

and each stage can fail. If the references disarm BEFORE the parse, every stage
is untrapped. If they disarm only on success, an early failure should still trap.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# Line 10 of the fixture is `ON ERROR GOTO 900`, so a handler is ALWAYS armed
# when these run. Each row's own CLS clears the LIST echo, so an UNTRAPPED
# message is readable instead of being read back as source text.
# --- stage 1: the GOTO token is wrong ---------------------------------------
add('a.nogoto',  ['CLS', 'ON ERROR PRINT'],        '"bail-missed"')
# --- stage 2: the operand is not a line number ------------------------------
add('a.badtok',  ['CLS', 'ON ERROR GOTO A'],       '"bail-missed"')
add('a.badstr',  ['CLS', 'ON ERROR GOTO "X"'],     '"bail-missed"')
# --- stage 3: a well-formed line number that does not exist -----------------
add('a.undef',   ['CLS', 'ON ERROR GOTO 12345'],   '"bail-missed"')
# --- 🟢 the handler IS armed at this point (the control that says stages 1-3
#     are about ON ERROR and not about a missing handler) ---------------------
add('c.armed',   ['CLS', 'A=1/0'],                 '"bail-missed"')
add('c.rearm',   ['ON ERROR GOTO 900', 'A=1/0'],   '"bail-missed"')
# --- does a FAILED ON ERROR leave the OLD handler armed for the NEXT error? --
# The discriminator: if the reference disarms before parsing, the error on the
# following line is untrapped too.
add('d.next',    ['ON ERROR GOTO 900', 'CLS', 'A=1/0'], '"bail-missed"')
# --- 🔴 THE DISCRIMINATOR THE FIRST ROUND NEEDED ----------------------------
# `a.nogoto` (wrong GOTO token, EARLIER stage) and `a.undef` (undefined line,
# LATER stage) both TRAP on all three sides -- so "the reference disarms before
# parsing" is REFUTED, and only the $0E operand stage differs. The remaining
# explanation is that the references never RUN the statement at all: MSX BASIC
# crunches `ON ERROR GOTO <number>` and may reject a non-numeric operand at
# TOKENISATION, in direct mode, before the program is ever stored.
# 🎯 These rows separate the two: if the line was REJECTED AT ENTRY it is simply
# absent, the program runs on, and the value line reports the LATER statement's
# result. If it was stored and raised untrapped, no value is reported at all.
add('t.stored',  ['CLS', 'ON ERROR GOTO A', 'B=9'],   'B')
add('t.stored2', ['CLS', 'ON ERROR GOTO "X"', 'B=9'], 'B')
# 🟢 the same shape with a VALID target -- the line is stored and B=9 runs, so a
# reading of 9 here is what "the line was skipped" would look like. Without this
# control, a 9 above could not be told from a working program.
add('t.ctl',     ['CLS', 'ON ERROR GOTO 900', 'B=9'], 'B')

# --- 🟢 controls ------------------------------------------------------------
add('ctl.num',   [], '1+1')
add('ctl.goto0', ['ON ERROR GOTO 0'], '"armed"')

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
    # detect the ECHO, on EVERY side (D-NGRAM10 §3)
    if any(any(m in str(res[s].get(l)) for m in ("<NO OUTPUT>", "<NO CAPTURE>", ';"'))
           for s in sides):
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}" + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
