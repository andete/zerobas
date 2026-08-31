#!/usr/bin/env python3
r"""D-PLAYCORNER — the three unmeasured PLAY corners the D-MUSICF review filed.

Each row's question is ACCEPT vs REJECT, read through PLAY(1) after the
statement: an accepted string leaves a ~7.5 s L1 note sounding (-1); a rejected
one raises before anything is queued (0). The L1 length is what makes the
reading stable against the harness pacing (the D-MUSICF lesson).

  w.ok     🟢 PLAY"T32L1C"      accepted everywhere -- the -1 control that
           proves an ACCEPT is visible at all
  w.twrap  PLAY"T65568L1C"     65568 wraps to 32 in a 16-bit accumulator and
           PASSES this tree's range check. Does the reference accept it?
  w.owrap  PLAY"O65537L1C"     65537 -> 1 the same way
  w.vwrap  PLAY"V65551L1C"     65551 -> 15
  c.cflat  PLAY"O1L1C-"        note underflow: this tree clamps to note 0
  c.bsharp PLAY"O8L1B#"        note overflow: this tree clamps to note 95
  m.zero   PLAY"M0L1C"         envelope period 0: this tree stores it
  ctl.bad  🟢 PLAY"T31L1C"      out of range WITHOUT wrapping -- rejected
           everywhere (ERR 5), the 0 control that proves a REJECT is visible

⚠️ SCOPE: accept-vs-reject only. If a clamp row ACCEPTS on both sides, whether
the reference plays the SAME PITCH as the clamp is a separate question needing
a PSG trace row (basic_probe_playtrace.py's method), not a screen read.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D                                    # noqa: E402

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

add('w.ok',     ['PLAY"T32L1C"'],     'PLAY(1)')
add('w.twrap',  ['PLAY"T65568L1C"'],  'PLAY(1)')
add('w.owrap',  ['PLAY"O65537L1C"'],  'PLAY(1)')
add('w.vwrap',  ['PLAY"V65551L1C"'],  'PLAY(1)')
add('c.cflat',  ['PLAY"O1L1C-"'],     'PLAY(1)')
add('c.bsharp', ['PLAY"O8L1B#"'],     'PLAY(1)')
add('m.zero',   ['PLAY"M0L1C"'],      'PLAY(1)')
# the two rows that DECIDE the overflow fix's shape for M (16-bit domain):
# saturate-to-$FFFF would ACCEPT M65600 as 65535; reject-on-wrap would not.
add('m.max',    ['PLAY"M65535L1C"'],  'PLAY(1)')
add('m.wrap',   ['PLAY"M65600L1C"'],  'PLAY(1)')
add('ctl.bad',  ['PLAY"T31L1C"'],     'PLAY(1)')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>12}" for s in sides) + "   verdict")
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
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>12}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}"
      + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
raise SystemExit(1 if diff else 0)
