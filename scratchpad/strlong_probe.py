#!/usr/bin/env python3
r"""D-STRLONG — the STRMAX clamp diverges, and the filing runs TWO defects together.

TODO.md (filed 2026-08-28 by D-CONCATPEAK, docs/spec-concatpeak.md §8) says
`sh_append` clamps a combined length over 255 to 255, and that its header calls
that "reference left-to-right truncation" -- which is exactly what neither
reference does. Both raise `String too long` (ERR 15).

🎯 THE FILING NAMES TWO DEFECTS AND THIS PROBE'S JOB IS TO SEPARATE THEM:

  D1  SILENT CLAMP.        Pool big enough for the clamped result: zerobas
                           returns 255 / "AAA"; both references raise ERR 15.
  D2  ERROR PRECEDENCE.    Pool NOT big enough: zerobas reports ERR 14 ("Out of
                           string space"); both references still report ERR 15,
                           because they test the LENGTH before they touch the
                           pool.

They are separated by ONE knob -- the pool size -- so the row set sweeps CLEAR
across the whole range for a fixed over-255 concatenation. If D2 is a mere
consequence of D1 (i.e. the length test, once added, runs before any
allocation), then a fix at the clamp site turns EVERY row in the sweep to
ERR 15 at once. If D2 survives, the low-CLEAR rows stay ERR 14 and the real
site is upstream, in `str_concat_tail`'s operand-1 snapshot.

🟢 AND THE ROWS THAT MUST NOT MOVE. `e.255` is a concatenation of EXACTLY 255
bytes: legal on all three sides today and legal after any fix. Without it a
"fix" that raises ERR 15 one byte early scores perfect on every other row.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- controls: nothing below is a reading if one of these moved -------------
CTL_WANT = {'ctl.num': '2', 'ctl.str': 'HI', 'ctl.cat': 'ABCD'}
add('ctl.num', [], '1+1')
add('ctl.str', ['A$="HI"'], 'A$')
add('ctl.cat', ['A$="AB":B$="CD"'], 'A$+B$')

# --- the four FILED rows, verbatim ------------------------------------------
add('f.len3',  ['CLEAR 900', 'X$=STRING$(200,"A")'], 'LEN(X$+X$+X$)')
add('f.right', ['CLEAR 900', 'X$=STRING$(200,"A")'], 'RIGHT$(X$+X$,3)')
add('f.128',   ['X$=STRING$(128,"A")'],              'LEN(X$+X$)')
add('f.200',   ['X$=STRING$(200,"A")'],              'LEN(X$+X$)')

# --- D1 / D2 separator: ONE over-255 concat, pool swept ---------------------
# X$ is 128 -> X$+X$ = 256, one byte over. The reference answer is ERR 15 at
# EVERY pool size; zerobas's answer is what tells D1 from D2.
for c in (200, 300, 400, 500, 600, 900):
    add(f's.{c}', [f'CLEAR {c}', 'X$=STRING$(128,"A")'], 'LEN(X$+X$)')

# --- the exact boundary, both sides of 255 ----------------------------------
add('e.255', ['CLEAR 900', 'X$=STRING$(200,"A")', 'Y$=STRING$(55,"B")'],
             'LEN(X$+Y$)')                        # 🟢 legal -- must stay 255
add('e.256', ['CLEAR 900', 'X$=STRING$(200,"A")', 'Y$=STRING$(56,"B")'],
             'LEN(X$+Y$)')                        # one over
# 🟢 a legal 255 built by a THREE-operand fold, so the fix is scored on the
# loop's later iterations too, not only its first append.
add('e.255x3', ['CLEAR 900', 'X$=STRING$(100,"A")', 'Y$=STRING$(55,"B")'],
               'LEN(X$+X$+Y$)')
add('e.256x3', ['CLEAR 900', 'X$=STRING$(100,"A")', 'Y$=STRING$(56,"B")'],
               'LEN(X$+X$+Y$)')

# --- is the clamp visible anywhere OTHER than LEN? --------------------------
# (a `v.assign` row -- the failing concat in a SETUP line, read back with
# LEN(A$) -- was dropped: the setup line errors on ALL THREE sides, so the
# harness echoes the typed line and the row is NO READING on any of them.
# [[an-unnamed-outcome-reads-as-no-outcome]])
add('v.mid',    ['CLEAR 900', 'X$=STRING$(200,"A")'], 'MID$(X$+X$,255,1)')

# --- 🔴 A TERM STILL PENDING AFTER THE FAILING APPEND ------------------------
# str_concat_tail's error tail returns with HL just past the operand that
# failed, so any `+ term` still to its RIGHT is left in the text and re-parsed
# as a NUMERIC continuation. `x.oom3` triggers the identical shape through
# SH_ERR=1 (a plain pool OOM), which is code that PREDATES D-STRLONG -- so the
# row says whether the tail is a pre-existing defect this slice merely exposes,
# or something D-STRLONG introduced. `x.oom2` is the 2-operand control: same
# pool, same OOM, nothing pending.
add('x.oom2',    ['CLEAR 250', 'X$=STRING$(100,"A")'], 'LEN(X$+X$)')
add('x.oom3',    ['CLEAR 250', 'X$=STRING$(100,"A")'], 'LEN(X$+X$+X$)')
add('x.long4',   ['CLEAR 900', 'X$=STRING$(200,"A")'], 'LEN(X$+X$+X$+X$)')
add('x.longtail',['CLEAR 900', 'X$=STRING$(200,"A")', 'Y$="Z"'], 'LEN(X$+X$+Y$)')

# --- how big IS the default pool? (characterization, not gated) -------------
add('d.fre', [], 'FRE("")')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}

dead = []
for c, want in sorted(CTL_WANT.items()):
    got = str(res.get("zb", {}).get(c))
    print(f"{'CTL':<6} {c:<10} want {want!r:<8} got {got!r}")
    if got != want: dead.append(c)
if dead:
    print(f"\n🔴 CONTROL ROW(S) FAILED: {' '.join(dead)} — the machine is broken "
          f"and NO row below is a reading.")
    raise SystemExit(2)
print()

subj = [l for l in ORDER if l not in CTL_WANT]
w = max(len(l) for l in subj)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides) + "   verdict")
diff = []
for l in subj:
    zb = str(res["zb"].get(l))
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    # an echo of the typed line is NO READING, not a pass
    echo = lambda t: any(k in t for k in ("LEN(", "STRING$", "MID$"))
    # 🔴 an echo on the REFERENCE side is just as much "no reading" as one on
    # zerobas's, and the first cut of this fence only looked at zb.
    fence = "🔴 ECHO" if (echo(zb) or any(echo(r) for r in refs)) else ""
    same = all(r == zb for r in refs)
    if not same: diff.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'} {fence}")
print(f"\nDIFF vs references: {len(diff)}/{len(subj)}"
      + ("  " + " ".join(diff) if diff else ""))

# --- D1 vs D2 readout -------------------------------------------------------
print("\n--- D1 (silent clamp) vs D2 (precedence), from the CLEAR sweep ---")
for c in (200, 300, 400, 500, 600, 900):
    l = f's.{c}'
    zb = str(res["zb"].get(l))
    kind = ("D2 precedence — reports ERR 14" if "string space" in zb.lower()
            else "D1 silent clamp — returns the truncated value" if zb.strip() in ("255", "256")
            else "✅ String too long (matches both references)" if "too long" in zb.lower()
            else f"🔴 UNCLASSIFIED: {zb!r}")
    print(f"  CLEAR {c:<4d} zb={zb!r:<28} {kind}")
