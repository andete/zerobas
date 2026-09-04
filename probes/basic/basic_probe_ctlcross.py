#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CTLCROSS -- what a `NEXT` does when a GOSUB frame is IN THE WAY.

WHY THIS EXISTS. The control-frame-pool arc (TODO.md, out of D-STACKPOOL) turns
`GSP`/`FSP`/`TRAPSVC` into pointers into ONE descending pool. zerobas today has
THREE SEPARATE ARRAYS (`GOSUB_STK`, `FOR_STK`, `TRAPSTK`), and separate arrays
make a whole class of question INVISIBLE: a `NEXT` can always reach its `FOR`
frame, because no GOSUB frame can ever be between them. Put the frames in one
pool and they interleave, and the machine has to answer.

🔴 THE ANSWER IS MEASURED, AND ZEROBAS IS ON THE WRONG SIDE OF IT (2026-09-04).
Both references raise `NEXT without FOR` (ERR 1) whenever the matching `FOR`
frame lies below a live GOSUB frame; zerobas matches straight across and runs the
loop. Three rows, both references agreeing on every one:

    row         vg8020   cf3300   zb        what the row does
    x.nxgos      0 1      0 1     1 0       NEXT inside a sub, FOR outside
    x.nxdeep     0 1      0 1     1 0       NEXT I across [FOR J][GOSUB][FOR I]
    x.nxagain    0 1      0 1     2 0       ...and the loop-CONTINUES arm

🎯 SO THE POOL IS NOT ONLY ABOUT DEPTH. A single descending pool whose `NEXT`
search stops at the first non-`FOR` frame answers all three the way both
references do, for no extra mechanism -- the divergence exists BECAUSE the
stacks are separate. These rows are the pool arc's behavioural acceptance, and
until it lands they are pinned as known-divergent below.

READING. Each row prints `[R E]`: R = 1 iff the statement after the cross-`NEXT`
ran (x.nxagain reports the handler-entry COUNT there instead), E = the ERR that
stopped the program, 0 = none. The GOSUB frame's fate is E:

    E=0  the NEXT left the GOSUB frame standing; the later RETURN worked
    E=3  `RETURN without GOSUB` -- the NEXT consumed the frame it walked past
    E=1  `NEXT without FOR`     -- the NEXT never saw the FOR at all

⚠️ `x.ctl` IS READ AS A PRECONDITION, NOT AS A ROW. It is the same program with
the `FOR` opened INSIDE the subroutine, so no frame interleaves and every machine
must read `1 0`. If it diverges, nothing else in the run is readable as a finding
and the probe refuses rather than reporting one.

⚠️ EVERY ROW `CLS`ES BEFORE ITS FENCE and the reader is digits-only. A run that
never reaches its `PRINT` leaves the ECHO of that line on screen, and `[";R;E;"]`
is not a reading -- the fault `scratchpad/trapsvc_probe.py` documents and
`scratchpad/stackpool_probe.py` was bitten by.
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

TAIL = ["800 E=ERR:RESUME900",
        '900 CLS:PRINT"[";R;E;"]":END']

# label, kind ("ctl" = precondition), program, what it does
CASES = [
    ("x.ctl", "ctl",
     ["10 ONERRORGOTO800", "20 E=0:R=0",
      "40 GOSUB100",
      "50 GOTO900",
      "100 FORI=1TO1",
      "110 NEXTI",
      "120 R=1",
      "130 RETURN", *TAIL],
     "FOR opened INSIDE the sub -- nothing interleaves"),

    # 🎯 THE SUBJECT. At the `NEXT` the frame order is [GOSUB][FOR] with the
    # GOSUB's the newer, so a pooled machine must decide whether the search
    # crosses it. E is the whole reading.
    ("x.nxgos", "row",
     ["10 ONERRORGOTO800", "20 E=0:R=0",
      "30 FORI=1TO1",
      "40 GOSUB100",
      "50 GOTO900",
      "100 NEXTI",
      "110 R=1",
      "120 RETURN", *TAIL],
     "NEXT inside a sub, FOR opened outside it"),

    # THE DEEPER INTERLEAVE, [FOR J][GOSUB][FOR I] with the NEXT naming the
    # OUTERMOST. A named NEXT already discards inner FOR frames; this asks
    # whether that walk also crosses a GOSUB frame.
    ("x.nxdeep", "row",
     ["10 ONERRORGOTO800", "20 E=0:R=0",
      "30 FORI=1TO1",
      "40 GOSUB100",
      "50 GOTO900",
      "100 FORJ=1TO1",
      "110 NEXTI",
      "120 R=1",
      "130 RETURN", *TAIL],
     "NEXT I across [FOR J][GOSUB][FOR I]"),

    # ⚠️ THE LOOP-CONTINUES ARM, which the two rows above CANNOT reach: both end
    # their loop on the first NEXT (`TO 1`), so both exercise only the
    # loop-ENDS exit. Here the NEXT resumes the loop BODY -- which is the GOSUB
    # on line 40 -- so a second GOSUB frame is pushed with the first standing.
    # R carries the handler-entry COUNT, so a machine that stops early says so
    # rather than reading like a machine that never started.
    ("x.nxagain", "row",
     ["10 ONERRORGOTO800", "20 E=0:R=0:N=0",
      "30 FORI=1TO2",
      "40 GOSUB100",
      "50 GOTO900",
      "100 N=N+1",
      "110 NEXTI",
      "120 R=N",
      "130 RETURN", *TAIL],
     "the NEXT resumes the loop body = the GOSUB (R = entry count)"),

    # THE MIRROR DIRECTION, and it is ALREADY faithful: a RETURN discarding the
    # FOR frames opened since its GOSUB (D-FORRET, docs/spec-basic-forret.md).
    # Re-run here so both directions are read on one apparatus -- a pooled
    # design gets this for free and must not lose it.
    ("x.retfor", "row",
     ["10 ONERRORGOTO800", "20 E=0:R=0",
      "40 GOSUB100",
      "50 R=1:NEXTJ",
      "60 GOTO900",
      "100 FORJ=1TO1",
      "110 RETURN", *TAIL],
     "RETURN over an inner FOR, then NEXT J outside"),
]

# row -> (reference, zerobas): the CURRENT truth, measured 2026-09-04 on both
# references. 🔴 THESE THREE ARE THE POOL ARC'S ACCEPTANCE. When it lands they
# become agreements and this gate goes RED until the pins are REMOVED -- which
# is deliberate: a fixed row that keeps its pin goes back to looking normal.
PINNED = {
    "x.nxgos":   ("0 1", "1 0"),
    "x.nxdeep":  ("0 1", "1 0"),
    "x.nxagain": ("0 1", "2 0"),
}

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
}

NUM = re.compile(r"^[-0-9 ]+$")


def face(raw):
    """The digits-only fence reader. A run that never reaches its own PRINT
    leaves the ECHO of that line, and `[";R;E;"]` is not a reading."""
    for m in re.finditer(r"\[([^\[\]]*)\]", "".join(raw or "")):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split())
    return "<NO OUTPUT>"


def run(machine, boot, reset, sel):
    caps = omsx_repl.run_cases(
        machine, [(lab, list(reset) + prog + ["RUN"]) for lab, _k, prog, _w in sel],
        batch=False, reset=(), boot=boot, step=20.0, cap_gap=10.0, timeout=300.0)
    return [face(c) for c in caps]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only", help="substring filter on the row label")
    ap.add_argument("--gate", action="store_true",
                    help="exit non-zero on an unpinned divergence or a pin drift")
    args = ap.parse_args()

    sel = [c for c in CASES if not args.only or args.only in c[0]]
    # ⚠️ x.ctl is a PRECONDITION and is re-added whatever --only says: no row
    # here is readable as a finding while the no-interleave control diverges.
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

    blank = sorted({lab for s in got for lab, v in got[s].items()
                    if v == "<NO OUTPUT>"})
    if blank:
        print(f"INSTRUMENT FAULT: no reading on {blank} -- no verdict. "
              f"A row that printed nothing is NOT MEASURED, never agreement.")
        return 2

    # --- the ORACLE check, before any verdict is read as a finding -----------
    split = [lab for lab in got["vg8020"]
             if got["vg8020"][lab] != got["cf3300"][lab]]
    if split:
        print(f"⚠️ THE TWO REFERENCES DISAGREE on {split} -- there is no single "
              f"reference answer for those rows and none of them is a finding.")
        return 1

    ctl_bad = [lab for lab, k, _p, _w in sel
               if k == "ctl" and got["zb"][lab] != got["vg8020"][lab]]
    if ctl_bad:
        print(f"⚠️ THE NO-INTERLEAVE CONTROL DIVERGED ({', '.join(ctl_bad)}) -- "
              f"nothing else in this run is readable as a D-CTLCROSS finding.")
        return 1

    print(f"\n{'row':<11} {'vg8020':>8} {'cf3300':>8} {'zb':>8}   verdict")
    bad = []
    for lab, _k, _p, why in sel:
        r, g = got["vg8020"][lab], got["zb"][lab]
        if lab in PINNED:
            want = PINNED[lab]
            if (r, g) == want:
                tag = "known-divergent, pinned"
            else:
                bad.append(lab)
                tag = f"🔴 PIN DRIFT from {want}"
        elif r == g:
            tag = "ok"
        else:
            bad.append(lab)
            tag = "🔴 UNPINNED DIVERGENCE"
        print(f"{lab:<11} {r:>8} {got['cf3300'][lab]:>8} {g:>8}   {tag}   {why}")

    print(f"\nrows {len(sel)}  pinned {len(PINNED)}  red {len(bad)}")
    if bad:
        print("  🔴 A PIN MOVED. If the control-frame-pool arc landed, these rows "
              "getting FIXED is the news -- REMOVE the pin in the same commit; an "
              "un-updated pin is how a fixed row goes back to looking normal.")
    print("CTLCROSS: PASS" if not bad else f"CTLCROSS: RED ({len(bad)})")
    return 1 if (bad and args.gate) else 0


if __name__ == "__main__":
    sys.exit(main())
