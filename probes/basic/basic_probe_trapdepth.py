#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TRAPDEPTH -- what does the REFERENCE RECLAIM when a trap handler is abandoned?

WHY THIS EXISTS. `docs/spec-basic-trapsvc.md` §6 declined a fix and ranked three
options on a premise NOBODY HAD MEASURED: that the reference reclaims the
abandoned dispatch, so zerobas's cap is a leak the references do not have. These
rows measure it, and the premise is FALSE (§10, 2026-09-04):

    row        vg8020   cf3300   zb        what it is
    d.depth0    4071      3302    8        plain recursion depth, no trap at all
    d.depth20   4016      3247    -        ...after TWENTY abandoned dispatches
    d.ctl20     4040      3271    8        the SAME program, `INTERVAL ON` removed

**≈1 frame per abandoned dispatch, on both references -- the same as zerobas.**
Nothing is reclaimed anywhere; the difference is CAPACITY, which is what
D-STACKPOOL then explained (one HIMEM-bounded pool, `basic_probe_stackpool.py`).

⚠️ `d.ctl20` IS THE ROW THAT MAKES THE OTHERS MEAN ANYTHING. It is byte-for-byte
`d.depth20` with the one `INTERVAL ON` removed, so program text, variable count
and loop overhead are identical and the whole difference is the cost of twenty
dispatches. The raw `d.depth0` baseline cannot hold those constant.

⚠️ `F` COUNTS ACTUAL HANDLER ENTRIES, and it is not decoration -- it caught two
faults that each read like the finding the slice was looking for:
  1. `d.depth20`'s handler resumed PAST the loop tail, so it fired ONCE and fell
     through to the recursion. The row would have read "nineteen more dispatches
     are free", arrived at because nothing happened. `RESUME 28`, not 29.
  2. An earlier `d.depth1` resumed to the PRINT line and read `0 18` on all three
     sides -- agreeing everywhere because the program ended before the
     measurement began.
Both are the same shape: a row that agrees, or reads flat, because its subject
never ran [[a-case-that-agrees-can-agree-for-the-wrong-reason]].

⚠️ `d.selfarm` IS A GUARD, NOT A MEASUREMENT. A handler that re-enables its OWN
trap and then RETURNs is the case §6 warns a fix must not break; it reads `9 0`
on all three machines TODAY. The control-frame-pool arc must leave it there.

ON INTERVAL is the instrument because it is the ONLY self-firing MSX1 trap --
KEY/STRIG/SPRITE/STOP need a human -- and all five share `check_traps` and
`trap_return_check` verbatim (the index is a parameter).
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
}

JIF = 0xFC9E            # published work area: the frame counter


def wait(line, n):
    """Let n FRAMES pass, machine-independently, with the high-byte re-read
    guard: a lo-then-hi read TEARS when the low byte wraps between the two PEEKs
    and composes 256 low."""
    return [f"{line} H=PEEK(&H{JIF+1:X}):W=PEEK(&H{JIF:X})+256*H"
            f":IFH<>PEEK(&H{JIF+1:X})THEN{line}",
            f"{line+1} H=PEEK(&H{JIF+1:X}):V=PEEK(&H{JIF:X})+256*H"
            f":IFH<>PEEK(&H{JIF+1:X})THEN{line+1}",
            f"{line+2} IFV-W<{n}THEN{line+1}"]


# 🔴 `RESUME 28`, NOT 29 -- see the docstring's fault 1. 28 is the loop-CONTINUE
# line, so the handler returns INTO the loop; d.depth0/d.depth1 have no loop and
# 28 is their own REM / INTERVAL OFF.
_TAIL = ['90 CLS:PRINT"[";D;E;F;"]":END',
         "600 D=D+1:GOSUB600",
         "610 RETURN",
         "700 C=1:F=F+1:X=FNZ(0)",
         "710 RETURN",
         "800 IFD=0THENRESUME28",
         "810 E=ERR:RESUME90"]

_DEPTH20 = ["10 ONERRORGOTO800",
            "20 ONINTERVAL=10GOSUB700",
            "22 M=0:F=0",
            "24 D=0:E=0:C=0:INTERVALON",
            *wait(25, 45),
            "28 INTERVALOFF:M=M+1:IFM<20THEN24",
            "30 GOSUB600",
            *_TAIL]

CASES = [
    ("d.depth0", ["10 ONERRORGOTO800", "20 D=0:E=0:F=0", "28 REM", "30 GOSUB600",
                  *_TAIL],
     "plain recursion depth, no trap at all"),
    ("d.depth1", ["10 ONERRORGOTO800",
                  "20 ONINTERVAL=10GOSUB700",
                  "25 D=0:E=0:F=0:C=0:INTERVALON",
                  *wait(26, 45),
                  "28 INTERVALOFF",
                  "30 GOSUB600",
                  *_TAIL],
     "...after ONE abandoned dispatch"),
    ("d.depth20", _DEPTH20, "...after TWENTY abandoned dispatches"),
    # 🎯 THE SAME-SIZE CONTROL: byte-for-byte d.depth20 with the one `INTERVAL ON`
    # removed, so the trap never fires and the only difference is the dispatches.
    ("d.ctl20", [l.replace(":INTERVALON", "") for l in _DEPTH20],
     "the SAME program, trap unarmed -- the cost of 20 dispatches"),
    # A GUARD, not a measurement: the handler re-enables its own trap and RETURNs
    # (spec-basic-trapsvc.md §6 warns a fix must not break it).
    ("d.selfarm", ["10 ONERRORGOTO800",
                   "20 ONINTERVAL=10GOSUB700",
                   "30 N=0:E=0:INTERVALON",
                   *wait(40, 90),
                   '50 INTERVALOFF:CLS:PRINT"[";N;E;"]":END',
                   "700 N=N+1:INTERVALON:RETURN",
                   "800 E=ERR:RESUME50"],
     "GUARD: a handler that re-arms its OWN trap, then RETURNs"),
]

# row -> (reference, zerobas), the CURRENT truth measured 2026-09-04.
# ⚠️ `<NO OUTPUT>` IS A NAMED OUTCOME HERE, NOT A MISSING ONE. zerobas caps at
# SIX abandoned dispatches (TRAPSTK_MAX = 6), so d.depth20's twentieth cycle
# raises ERR 7 inside an already-active error handler; that is untrapped, the
# program ABORTS and the fence is never printed. Pinning it says which of the
# two it is -- an unnamed outcome reads as no outcome
# [[an-unnamed-outcome-reads-as-no-outcome]].
PINNED = {
    "d.depth0":  ("4071 7 0", "8 7 0"),
    "d.depth1":  ("4046 7 0", "8 7 0"),
    "d.depth20": ("4016 7 20", "<NO OUTPUT>"),
    "d.ctl20":   ("4040 7 0", "8 7 0"),
}
# 🎯 THE GUARD, and it must read the SAME on all three. Not a divergence pin: a
# row all three agree on, recorded so a fix that breaks it goes red here.
GUARD = {"d.selfarm": "9 0"}

# The reference's own finding, checked before any zerobas verdict is read: the
# per-dispatch cost of twenty abandoned dispatches, on each reference, in frames.
LEAK_ROWS = ("d.ctl20", "d.depth20")
LEAK_EXPECT = 24
LEAK_TOL = 4          # the rows reproduced at exactly 24/24 twice; a few frames
                      # of slack keeps a timing wobble from reading as a finding

NUM = re.compile(r"^[-0-9 ]+$")


def face(raw):
    for m in re.finditer(r"\[([^\[\]]*)\]", "".join(raw or "")):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split())
    return "<NO OUTPUT>"


def run(machine, boot, reset, sel):
    caps = omsx_repl.run_cases(
        machine, [(lab, list(reset) + prog + ["RUN"]) for lab, prog, _w in sel],
        batch=False, reset=(), boot=boot, step=60.0, cap_gap=15.0, timeout=420.0)
    return [face(c) for c in caps]


def num(v, i=0):
    try:
        return int(v.split()[i])
    except (ValueError, IndexError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only", help="substring filter on the row label")
    ap.add_argument("--gate", action="store_true",
                    help="exit non-zero on a pin drift or a broken precondition")
    args = ap.parse_args()

    sel = [c for c in CASES if not args.only or args.only in c[0]]
    if not sel:
        print("no rows selected")
        return 2

    reads = {}
    for side, kw in list(SIDES.items()) + [("zb", dict(machine=args.zb_machine,
                                                       boot=8.0, reset=("NEW",)))]:
        reads[side] = dict(zip([c[0] for c in sel],
                               run(kw["machine"], kw["boot"], kw["reset"], sel)))

    sides = ["vg8020", "cf3300", "zb"]
    # ⚠️ A `<NO OUTPUT>` is only an instrument fault where it is NOT the pinned
    # answer. On the references it always is one; on zerobas d.depth20's is the
    # measured abort, and pinning it is what tells the two apart.
    blank = sorted({f"{s}/{lab}" for s in sides for lab, v in reads[s].items()
                    if v == "<NO OUTPUT>"
                    and not (s == "zb" and PINNED.get(lab, (None, None))[1] == v)})
    if blank:
        print(f"INSTRUMENT FAULT: no reading on {blank} -- NOT MEASURED, and not "
              f"agreement. Check F (the handler-entry count) first.")
        return 2

    w = max(len(l) for l, _, _ in CASES)
    print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>12}" for s in sides) + "   note")
    for lab, _p, why in sel:
        print(f"{lab:<{w}}  " + "  ".join(f"{reads[s][lab]:>12}" for s in sides)
              + f"   {why}")

    bad = []
    # --- the reference's own finding, before any zerobas verdict -------------
    if set(LEAK_ROWS) <= set(reads["vg8020"]):
        print()
        for s in ("vg8020", "cf3300"):
            a, b = (num(reads[s][l]) for l in LEAK_ROWS)
            if a is None or b is None:
                print(f"⚠️ {s}: the leak rows are not readable -- no verdict.")
                return 1
            cost = a - b
            ok = abs(cost - LEAK_EXPECT) <= LEAK_TOL
            print(f"  {s:<8} 20 abandoned dispatches cost {cost:>3} frames "
                  f"({cost / 20:.2f}/dispatch)   "
                  f"{'reproduces §10' if ok else '🔴 NOT §10s ' + str(LEAK_EXPECT)}")
            if not ok:
                print(f"⚠️ THE REFERENCE DID NOT REPRODUCE ITS OWN RESULT -- the "
                      f"oracle or the harness moved since spec-basic-trapsvc.md "
                      f"§10; no row in this run is readable.")
                return 1
        # ...and the dispatches must actually have HAPPENED (fault 1 above).
        for s in ("vg8020", "cf3300"):
            f = num(reads[s]["d.depth20"], 2)
            if f != 20:
                print(f"⚠️ {s}: F = {f}, not 20 -- the handler did not fire twenty "
                      f"times, so the frames above are not twenty dispatches' cost.")
                return 1

    print()
    for lab, _p, _w in sel:
        r, g = reads["vg8020"][lab], reads["zb"][lab]
        if lab in GUARD:
            want = GUARD[lab]
            agree = r == want and reads["cf3300"][lab] == want and g == want
            print(f"{lab:<{w}}  GUARD  all three must read {want!r}: "
                  + ("ok" if agree else "🔴 MOVED"))
            if not agree:
                bad.append(lab)
        elif lab in PINNED:
            want = PINNED[lab]
            if (r, g) == want:
                print(f"{lab:<{w}}  known-divergent, pinned {want}")
            else:
                bad.append(lab)
                print(f"{lab:<{w}}  🔴 PIN DRIFT from {want} to {(r, g)}")
        elif r == g:
            print(f"{lab:<{w}}  ok")
        else:
            bad.append(lab)
            print(f"{lab:<{w}}  🔴 UNPINNED DIVERGENCE  {r!r} vs {g!r}")

    print(f"\nrows {len(sel)}  pinned {len(PINNED)}  guards {len(GUARD)}  "
          f"red {len(bad)}")
    if bad:
        print("  🔴 A PIN MOVED. If the control-frame-pool arc landed, these rows "
              "changing is the news -- update PINNED in the same commit. A GUARD "
              "moving is never good news: d.selfarm is the case §6 warns about.")
    print("TRAPDEPTH: PASS" if not bad else f"TRAPDEPTH: RED ({len(bad)})")
    return 1 if (bad and args.gate) else 0


if __name__ == "__main__":
    sys.exit(main())
