#!/usr/bin/env python3
r"""D-TRAPDEPTH — what does the REFERENCE actually reclaim when a trap handler
is abandoned? Three questions the filed design assumed answers to.

The filed fix (spec-basic-trapsvc.md §6 option 3) is "pop the stale TRAPSTK
record when a SERVICING entry is explicitly re-armed". Reading the code first
turned up two problems with that:

  * `check_traps` pushes a GOSUB FRAME as well as a TRAPSTK record, and
    `int.six` needs NINE cycles. TRAPSTK_MAX is 6 and GOSUB_DEPTH is 8, so
    popping the record alone moves the cap 6 -> 8 and the row STILL fails.
  * §6 warns that popping when an entry leaves SERVICING breaks a handler that
    re-enables its OWN trap and then RETURNs. But that case and the abandoned
    one look IDENTICAL at the decision point: both are an explicit re-arm of a
    SERVICING entry whose record is on top, and RESUME does not unwind the GOSUB
    frame, so the saved GSP still matches in both.

🎯 SO THE REAL QUESTION IS NOT "WHERE DO WE POP" BUT "WHAT DOES THE REFERENCE
RECLAIM, IF ANYTHING". If it reclaims nothing and merely has more room, then no
cleanup logic is faithful and the answer is capacity. These rows separate that.

Reuses scratchpad/trapsvc_probe.py's fixture, `wait()` and `face()` -- including
face()'s digits-only guard, without which a run that never reaches its own
`PRINT` reports the ECHO of that line as a value.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trapsvc_probe as T                                         # noqa: E402

W = T.wait

# --- Q1: is the reference BOUNDED on repeated abandonment? -------------------
# int.six's shape, but to 40 cycles instead of 9. If a reference runs out too,
# it leaks as well and the difference is CAPACITY, not cleanup.
T.CASES['d.n40'] = ["10 ONERRORGOTO800",
                    "20 ONINTERVAL=10GOSUB700",
                    "30 N=0:E=0",
                    "40 INTERVALON:C=0",
                    *W(41, 45),
                    "50 IFC=0THEN90",
                    "52 N=N+1:IFN<40THEN40",
                    '90 INTERVALOFF:CLS:PRINT"[";N;E;"]":END',
                    "700 C=1:F=F+1:X=FNZ(0)",
                    "710 RETURN",
                    "800 E=ERR:RESUME50"]

# --- Q2: is the GOSUB FRAME reclaimed? --------------------------------------
# 🎯 THE SHARPEST PAIR. Recurse until the control stack overflows and report the
# depth reached. d.depth0 has no trap at all; d.depth1 runs ONE abandoned
# dispatch first. Equal depths = the frame was reclaimed. One less = it leaked.
# 🔴 THE FIRST CUT OF d.depth1 READ `0 18` ON ALL THREE AND MEASURED NOTHING.
# Its handler resumed to the PRINT line, so the trap's own fault ended the program
# before the recursion ever started. The handler now branches on D: D=0 means the
# fault came from the abandoned dispatch (carry on), D>0 means the recursion
# overflowed (report). A row that agrees on all three sides is not automatically
# a reading -- this one agreed because nothing had happened yet.
# ⚠️ F COUNTS ACTUAL HANDLER ENTRIES, and it is not decoration: without it the
# dispatch count is an ASSUMPTION. `d.depth20` loops twenty times, but nothing
# made the trap fire twenty times -- on a machine that stops dispatching, the row
# would read as "twenty dispatches cost nothing" when none happened.
_TAIL = ['90 CLS:PRINT"[";D;E;F;"]":END',
         "600 D=D+1:GOSUB600",
         "610 RETURN",
         "700 C=1:F=F+1:X=FNZ(0)",
         "710 RETURN",
         # 🔴 RESUME 28, NOT 29: resuming past the loop tail made d.depth20 fire
         # ONCE and then fall straight through to the recursion -- F said so (1,
         # not 20) and without F the row would have read "nineteen dispatches are
         # free". 28 is the loop-continue line, so the handler returns INTO the
         # loop. d.depth0/d.depth1 have no loop and 28 is their INTERVALOFF/REM.
         "800 IFD=0THENRESUME28",
         "810 E=ERR:RESUME90"]
T.CASES['d.depth0'] = ["10 ONERRORGOTO800", "20 D=0:E=0:F=0", "28 REM", "30 GOSUB600",
                       *_TAIL]
T.CASES['d.depth1'] = ["10 ONERRORGOTO800",
                       "20 ONINTERVAL=10GOSUB700",
                       "25 D=0:E=0:F=0:C=0:INTERVALON",
                       *W(26, 45),
                       "28 INTERVALOFF",
                       "30 GOSUB600",
                       *_TAIL]
# 🎯 THE ROW THAT SEPARATES "RECLAIMS" FROM "HAS ROOM". Twenty abandoned
# dispatches, then measure the depth still available. If the reference reclaims,
# this equals d.depth0; if it leaks, it is ~20 lower. Against 4080 that is a
# 0.5% difference, so d.depth0 has to be reproducible for it to mean anything --
# which is why d.depth0 is re-run here rather than quoted from the earlier table.
T.CASES['d.depth20'] = ["10 ONERRORGOTO800",
                        "20 ONINTERVAL=10GOSUB700",
                        "22 M=0:F=0",
                        "24 D=0:E=0:C=0:INTERVALON",
                        *W(25, 45),
                        "28 INTERVALOFF:M=M+1:IFM<20THEN24",
                        "30 GOSUB600",
                        *_TAIL]

# --- Q3: the case §6 warns a fix must not break ------------------------------
# The handler re-enables its OWN trap and then RETURNs. N counts the firings, so
# a machine that keeps firing reads a bigger number than one that stops at 1.
T.CASES['d.selfarm'] = ["10 ONERRORGOTO800",
                        "20 ONINTERVAL=10GOSUB700",
                        "30 N=0:E=0:INTERVALON",
                        *W(40, 90),
                        '50 INTERVALOFF:CLS:PRINT"[";N;E;"]":END',
                        "700 N=N+1:INTERVALON:RETURN",
                        "800 E=ERR:RESUME50"]

# 🎯 THE SAME-SIZE CONTROL. Byte-for-byte the d.depth20 program, with the one
# `INTERVALON` removed, so the trap never fires. Any depth difference between the
# two is the cost of TWENTY DISPATCHES and nothing else -- program text, variable
# count and loop overhead are identical, which is what the raw d.depth0 baseline
# could not hold constant.
T.CASES['d.ctl20'] = [l.replace(":INTERVALON", "") for l in T.CASES['d.depth20']]

ORDER = ['d.depth0', 'd.depth1', 'd.depth20', 'd.ctl20']
sides = ["vg8020", "cf3300", "zb"]
res = {s: {} for s in sides}
for s in sides:
    cfg = T.SIDES[s]
    for lab in ORDER:
        caps = T.omsx_repl.run_cases(
            cfg["machine"], [("direct", list(cfg["reset"]) + T.CASES[lab] + ["RUN"])],
            batch=False, reset=(), boot=cfg["boot"], step=60.0, cap_gap=15.0,
            timeout=420.0)
        res[s][lab] = T.face(caps[0])

w = max(len(l) for l in ORDER)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>14}" for s in sides) + "   verdict")
for lab in ORDER:
    v = [res[s][lab] for s in sides]
    tag = "refs agree" if v[0] == v[1] else "🔴 REFS SPLIT"
    zb = "" if v[1] == v[2] else "   zb DIFF"
    print(f"{lab:<{w}}  " + "  ".join(f"{x:>14}" for x in v) + f"   {tag}{zb}")
print("""
read: `[N E]` -- N is the count reached, E the ERR that stopped it (0 = never).
  d.depth0 vs d.depth1  EQUAL  -> the abandoned dispatch's GOSUB frame IS reclaimed
                        1 less -> it leaked
  d.n40    N=40 E=0     -> the reference reclaims and is effectively unbounded
           N<40         -> the reference leaks too; the gap is CAPACITY
  d.selfarm N>1         -> re-arming inside the handler keeps the trap alive""")
