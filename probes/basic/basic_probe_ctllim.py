#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CTLLIM -- does the control pool STAY OFF the variables as they grow?

WHY THIS EXISTS. D-CTLPOOL (docs/spec-basic-trapsvc.md §17) put control frames in
one pool that descends from `strheap_varceil()` and must stop at `ARYEND+2`, the
first byte the variable/array region does not own. That floor needs an
array-chain walk, which is sub-ROM knowledge, and a `subrom_call` per PUSH is not
affordable -- `FOR I=1 TO 1000:GOSUB 100:NEXT` pushes a thousand times. So the
floor is CACHED in `CTLLIM`, against `strheap_floor`'s own "DERIVED, NEVER
STORED" rule, and refreshed at every point the region's end can move.

🔴 THAT CACHE IS THE ARC'S WEAKEST JOINT, AND ITS FAILURE IS SILENT. A path that
grows the variable region without refreshing leaves `CTLLIM` **stale-LOW** -- the
dangerous direction -- and `ctl_alloc` then hands out frames INSIDE live
variables. Nothing raises; the program just gets wrong answers later. §17 filed
it as needing a gate. This is that gate.

🎯 THE ROWS TEST THE CORRUPTION, NOT THE POINTER. A probe that read `CTLLIM` back
would be asserting the implementation against itself. Instead each row fills
memory with a known pattern, drives the pool ALL THE WAY DOWN to its floor by
recursing until `Out of memory`, and then counts how many cells changed. `S` is
that count and it must be 0. A stale floor is exactly what makes it non-zero.

⚠️ BOTH ALLOCATORS ARE EXERCISED, AND THAT IS NOT PADDING. `scv_alloc` (scalars)
and `ary_alloc` (arrays) grow the region by different code with SEPARATE refresh
hooks (`sub/arrays.asm`, two call sites). A gate that only DIMmed an array would
leave the scalar hook completely untested, and a knife on it would pass.

⚠️ THE VERIFY LOOP IS `GOTO`-BASED, NEVER `FOR`. By the time it runs the pool is
EXHAUSTED -- that is the whole point of the row -- so a `FOR` there would need a
frame it cannot get and the row would read as an overflow instead of as a
corruption count. Nothing in the tail may push.

⚠️ AND THE `CLEAR` COMES BEFORE `ON ERROR`, as everywhere in this arc: `CLEAR`
resets the error vector, so the overflow would go untrapped and the row would
print nothing.

⚠️ THE EMULATED-TIME BUDGET IS 180 s AND THAT IS NOT PADDING. Every element of
`A()` crosses a SLOT on this machine (the array engine is a sub-ROM tenant), so
601 accesses plus a ~2500-frame recursion do not fit the 45 s the sibling probes
use. 🔴 AT 45 s BOTH BULK ROWS READ `<NO OUTPUT>` ON ZEROBAS ONLY -- which looks
exactly like the corruption this gate hunts, and the refusal message blamed the
verify tail. The separating runs were N=20-with-recursion (fine) and
N=300-without (fine): only the COMBINATION was slow, which is a budget, not a
defect. An unnamed outcome reads as no outcome, and a WRONGLY-named one is worse
[[an-unnamed-outcome-reads-as-no-outcome]].

🟢 THE REFERENCES PASS THESE ROWS TOO, which is what makes them a differential
rather than a zerobas-only assertion: their control frames come out of the same
gap (D-CTLSTACK §14), bounded below by `STREND`, so a `DIM` costs them depth in
exactly the same way and their variables survive the recursion in exactly the
same way.
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

N = 300          # array elements; ~2.4 KB of doubles, ~300 frames of depth
SCALARS = 60     # scalar variables, created after the pool's last reset

# The recursion + the trap, shared by every row. 800/810 are the recursion, 900
# is the handler. `RESUME 70` lands on the row's own verify tail.
_REC = ["800 D=D+1:GOSUB800",
        "810 RETURN",
        "900 E=ERR:RESUME70"]


def ary_prog():
    """DIM, fill, exhaust the pool, then count elements that changed."""
    return ["5 CLEAR 200",
            "10 ONERRORGOTO900",
            # 🎯 EVERY SCALAR IS CREATED BEFORE THE `DIM`, AND THE ORDER IS THE
            # WHOLE POINT OF THE ROW. CTLLIM is recomputed from scratch by
            # WHICHEVER allocator ran last, so a scalar created AFTER the array
            # refreshes the floor and covers for the array hook completely --
            # measured: knife K-CL2 (array hook removed) left this row GREEN
            # until these four moved up here. Make the DIM the LAST growth and
            # the array hook is the only thing that can refresh after it.
            "15 I=0:D=0:S=0:E=0",
            f"20 DIMA({N})",
            f"30 FORI=0TO{N}:A(I)=I:NEXT",
            "40 D=0:S=0:E=0",
            "50 GOSUB800",
            # --- the verify tail: GOTO-based, because the pool is now empty ---
            "70 I=0",
            "72 IFA(I)<>ITHENS=S+1",
            f"74 I=I+1:IFI<={N}THEN72",
            '76 CLS:PRINT"[";D;S;E;"]":END',
            *_REC]


def scal_prog():
    """The OTHER allocator. `SCALARS` two-character scalars, each set to a value
    derived from its own index, then the same exhaust-and-count."""
    # V0..V9, W0..W9, ... six letters x ten digits = 60 names, made and checked
    # by the same arithmetic so the row cannot agree by construction.
    names = [f"{c}{d}" for c in "VWXYZQ" for d in "0123456789"][:SCALARS]
    make, chk = [], []
    for i, nm in enumerate(names):
        make.append(f"{nm}={i}")
        chk.append(f"IF{nm}<>{i}THENS=S+1")
    # pack into short lines -- a line whose ECHO wraps breaks nothing here (the
    # fence is CLS'd) but a line over the tokeniser's limit would not store.
    def pack(items, first, step=2):
        out, ln = [], first
        for k in range(0, len(items), 5):
            out.append(f"{ln} " + ":".join(items[k:k + 5]))
            ln += step
        return out, ln
    mk, _ = pack(make, 20)
    ck, _ = pack(chk, 70)
    return ["5 CLEAR 200",
            "10 ONERRORGOTO900",
            *mk,
            "60 D=0:S=0:E=0",
            "62 GOSUB800",
            *ck,
            '95 CLS:PRINT"[";D;S;E;"]":END',
            *_REC]


def ctl_prog():
    """THE CONTROL. Five scalars, no bulk allocation, same recursion. Every
    machine must read S=0 -- if it does not, the tail itself is broken and the
    two rows above are not readable as findings."""
    return ["5 CLEAR 200",
            "10 ONERRORGOTO900",
            "20 P1=11:P2=22:P3=33:P4=44:P5=55",
            "40 D=0:S=0:E=0",
            "50 GOSUB800",
            "70 IFP1<>11THENS=S+1",
            "72 IFP2<>22THENS=S+1",
            "74 IFP3<>33THENS=S+1",
            "76 IFP4<>44THENS=S+1",
            "78 IFP5<>55THENS=S+1",
            '80 CLS:PRINT"[";D;S;E;"]":END',
            *_REC]


CASES = [
    ("l.ctl",  "ctl", ctl_prog(),  "CONTROL: five scalars, no bulk allocation"),
    ("l.ary",  "row", ary_prog(),  f"DIM A({N}), filled, then the pool driven down"),
    ("l.scal", "row", scal_prog(), f"{SCALARS} scalars -- the OTHER allocator"),
]

NUM = re.compile(r"^[-0-9 .E+]+$")


def face(raw):
    for m in re.finditer(r"\[([^\[\]]*)\]", "".join(raw or "")):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split())
    return "<NO OUTPUT>"


def run(machine, boot, reset, sel):
    caps = omsx_repl.run_cases(
        machine, [(lab, list(reset) + prog + ["RUN"]) for lab, _k, prog, _w in sel],
        batch=False, reset=(), boot=boot, step=180.0, cap_gap=20.0, timeout=600.0)
    return [face(c) for c in caps]


def parts(v):
    try:
        d, s, e = (int(float(x)) for x in v.split())
        return d, s, e
    except (ValueError, IndexError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only", help="substring filter on the row label")
    ap.add_argument("--gate", action="store_true", help="exit non-zero on a red row")
    args = ap.parse_args()

    sel = [c for c in CASES if not args.only or args.only in c[0]]
    if not any(c[1] == "ctl" for c in sel):
        sel = [c for c in CASES if c[1] == "ctl"] + sel
    if not sel:
        print("no rows selected")
        return 2

    got = {}
    for side, kw in list(SIDES.items()) + [("zb", dict(machine=args.zb_machine,
                                                       boot=8.0, reset=("NEW",)))]:
        got[side] = dict(zip([c[0] for c in sel],
                             run(kw["machine"], kw["boot"], kw["reset"], sel)))

    sides = ["vg8020", "cf3300", "zb"]
    # 🔴 A BLANK ON A **REFERENCE** IS AN INSTRUMENT FAULT; A BLANK ON ZEROBAS
    # ALONE IS THE FINDING'S LOUDEST FORM. A floor stale enough to let the pool
    # walk over the interpreter's own state does not print a corruption count --
    # it prints nothing, because the machine is gone. The first cut of this gate
    # returned 2 there and knife K-CL1 (which does exactly that) scored as "the
    # gate could not see it". A `<NO OUTPUT>` on one side only is a CONSEQUENCE
    # of the defect [[an-unnamed-outcome-reads-as-no-outcome]].
    ref_blank = sorted({f"{s}/{l}" for s in ("vg8020", "cf3300")
                        for l, v in got[s].items() if parts(v) is None})
    if ref_blank:
        print(f"INSTRUMENT FAULT: no reading on {ref_blank} -- a REFERENCE went "
              f"blank, so nothing here is readable.\n"
              f"  ⚠️ SUSPECT THE TIME BUDGET BEFORE THE MACHINE: every A() access "
              f"crosses a slot on zerobas, and at the sibling probes' 45 s both "
              f"bulk rows read blank. Re-run one row with --only and a smaller N "
              f"to separate slow from broken.\n"
              f"  ⚠️ Then check the verify tail is GOTO-based: the pool is "
              f"exhausted by the time it runs, so a FOR there cannot get a frame.")
        return 2

    w = max(len(l) for l, _, _, _ in CASES)
    print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>14}" for s in sides) + "   what it does")
    for lab, _k, _p, why in sel:
        print(f"{lab:<{w}}  " + "  ".join(f"{got[s][lab]:>14}" for s in sides)
              + f"   {why}")
    print("\nreads `[depth  corrupted-cells  ERR]`  -- S must be 0 everywhere\n")

    bad = []
    # --- every row, every side: nothing may be corrupted, and the recursion
    #     must actually have RUN OUT (ERR 7). A row that never overflowed never
    #     drove the pool to its floor and proves nothing.
    for lab, _k, _p, _w in sel:
        for s in sides:
            got_s = parts(got[s][lab])
            if got_s is None:                     # zerobas only, per the note above
                bad.append(f"{s}/{lab}")
                print(f"🔴 {s} {lab}: NOTHING PRINTED while both references "
                      f"answered. A floor stale enough to reach the interpreter's "
                      f"own state takes the machine with it -- that IS the "
                      f"corruption, in its loudest form.")
                continue
            d, corrupt, err = got_s
            if err != 7:
                bad.append(f"{s}/{lab}")
                print(f"🔴 {s} {lab}: stopped on ERR {err}, not 7 -- the pool was "
                      f"never driven to its floor, so S={corrupt} means nothing")
            elif corrupt:
                bad.append(f"{s}/{lab}")
                print(f"🔴 {s} {lab}: {corrupt} CELL(S) CORRUPTED after {d} frames "
                      f"-- the control pool descended INTO live variables. On "
                      f"zerobas that is CTLLIM stale-LOW (spec §17).")

    # --- 🎯 and the floor must MOVE with the region, or the cache is simply not
    #     tracking. An allocation has to COST depth, on every machine.
    if {"l.ctl", "l.ary"} <= set(got["zb"]):
        print("does an allocation COST depth? (the floor must rise with ARYEND)")
        for s in sides:
            a, b = parts(got[s]["l.ctl"]), parts(got[s]["l.ary"])
            if a is None or b is None:
                print(f"  {s:<8} <not readable -- see above>")
                continue
            base, with_ary = a[0], b[0]
            drop = base - with_ary
            ok = drop > 0
            print(f"  {s:<8} {base:>6} frames bare -> {with_ary:>6} with DIM A({N})"
                  f"   cost {drop:>5}   {'ok' if ok else '🔴 THE DIM COST NOTHING'}")
            if not ok:
                bad.append(f"{s}/track")

    print(f"\nrows {len(sel)}  red {len(bad)}")
    print("CTLLIM: PASS" if not bad else f"CTLLIM: RED ({len(bad)})")
    return 1 if (bad and args.gate) else 0


if __name__ == "__main__":
    sys.exit(main())
