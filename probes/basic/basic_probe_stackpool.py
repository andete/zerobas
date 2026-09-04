#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-STACKPOOL -- do control frames come out of a HIMEM-BOUNDED POOL, or an array?

WHY THIS EXISTS. zerobas caps GOSUB recursion at 8; the VG-8020 reaches ~4080 and
the CF-3300 ~3311. D-TRAPDEPTH established that neither reference RECLAIMS an
abandoned frame either, so the gap is not cleanup -- it is CAPACITY, and this
probe asks where the capacity comes from. `CLEAR n` resizes the string space and
`CLEAR n,addr` sets HIMEM outright, so if control frames and string space come
out of ONE pool, the reachable GOSUB depth must MOVE when that pool is resized --
and the size of the move gives the bytes per frame. If the depth does not move,
the frames live in a fixed array.

MEASURED 2026-09-04, and the answer is unambiguous (docs/spec-basic-trapsvc.md
§11): +2000 B of string space costs **286** frames on BOTH references and the
next +2000 costs 285/286 -- 7.0 B/frame, linear, four times over -- and pinning
HIMEM makes the two references agree **exactly** (2195 = 2195), which they
otherwise do not, because Disk BASIC had taken RAM on the CF-3300. zerobas reads
8 in every row.

🔴 WHAT THIS GATE MAY AND MAY NOT PIN. The two machines have different memory
maps BY CONSTRUCTION (C-BIOS vs a stock VG-8020), so an absolute depth is not a
shared quantity and never will be -- the same rule
`basic_probe_clearpool.py` states for `FRE(0)`. So no row here gates an absolute
number against the reference. What is gated is the MODEL:

  * SENSITIVITY  -- does the depth move at all when `CLEAR` resizes the pool?
  * LINEARITY    -- do the two +2000 B steps cost the same, i.e. is it one pool
                    at a constant bytes-per-frame rather than a coincidence?
  * THE HIMEM ROW -- with the ceiling pinned, do the two REFERENCES agree
                    exactly? That is the prediction a fixed array cannot make,
                    and it is checked between the references, where it means
                    something.
  * THE ERROR    -- every side must stop with ERR 7 (`Out of memory`).

✅ zerobas AGREES ON THE MODEL since the control-frame-pool arc landed
(2026-09-04): SENSITIVE+LINEAR, at 8.0 B/frame against the references' 7.0, and
~2866 frames against 4080 / 3311. The rate and the depth are per-machine and are
NOT gated -- the four bullets above are what is.

⚠️ THE `CLEAR` MUST COME BEFORE `ON ERROR`, AND THAT COST A WHOLE FIRST DRAFT.
With it after, every CLEAR row read `<NO OUTPUT>` on ALL THREE machines: `CLEAR`
RESETS THE ERROR VECTOR, so the overflow was untrapped, the program aborted and
nothing printed. The probe refused rather than reporting a value, which is the
only reason that read as an instrument fault instead of "CLEAR breaks recursion".

⚠️ `c.base` HAS NO `CLEAR` AT ALL. A row that fails to differ from it is saying
the `CLEAR` did nothing -- not that the pool is separate -- and the two readings
are not the same fact.
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

# label, the CLEAR that precedes the recursion, what the row is for
CASES = [
    ("c.base",    "",                 "no CLEAR at all -- the baseline"),
    ("c.clr200",  "CLEAR 200",        "small string space; the ladder's foot"),
    ("c.clr2200", "CLEAR 2200",       "+2000 B of string space"),
    ("c.clr4200", "CLEAR 4200",       "+4000 B -- the step must be LINEAR if shared"),
    ("c.himem",   "CLEAR 200,&HC000", "HIMEM lowered outright"),
]

STEP = 2000          # the string-space step between consecutive ladder rows
LADDER = ("c.clr200", "c.clr2200", "c.clr4200")

# ✅ THE POOL LANDED 2026-09-04, so there is no divergence left to pin: zerobas
# must now demonstrate the SAME MODEL as the references, and `PINNED` is empty.
# It read "INSENSITIVE" here until the arc; leaving that pin in place is how a
# fixed row goes back to looking normal, so it came out with the fix.
# ⚠️ THE MODEL, NOT THE NUMBER. zerobas reaches ~2866 frames at 8.0 B/frame
# against 4080 at 7.0 and 3311 at 7.0 -- the absolute depth and the rate are
# properties of each machine's map and its frame layout, and nothing here gates
# them. See the header.
PINNED = {}

# The references' own model, checked BEFORE any zerobas verdict is read as a
# finding. Not the absolute depths (which drift with the machine's own map) --
# the model they demonstrate.
REF_EXPECT = "SENSITIVE+LINEAR"

NUM = re.compile(r"^[-0-9 ]+$")


def face(raw):
    """Digits-only fence reader: a run that never reaches its own PRINT leaves
    the ECHO of that line, and `[";D;E;"]` is not a reading."""
    for m in re.finditer(r"\[([^\[\]]*)\]", "".join(raw or "")):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split())
    return "<NO OUTPUT>"


def program(clr):
    # 🔴 THE CLEAR IS LINE 5 -- BEFORE the `ON ERROR` on line 10. See the
    # docstring: the other order measures nothing, on every machine.
    return ([f"5 {clr}"] if clr else []) + [
        "10 ONERRORGOTO800",
        "20 D=0:E=0",
        "30 GOSUB600",
        '90 CLS:PRINT"[";D;E;"]":END',
        "600 D=D+1:GOSUB600",
        "610 RETURN",
        "800 E=ERR:RESUME90", "RUN"]


def run(machine, boot, reset, sel):
    caps = omsx_repl.run_cases(
        machine, [(lab, list(reset) + program(clr)) for lab, clr, _w in sel],
        batch=False, reset=(), boot=boot, step=45.0, cap_gap=15.0, timeout=420.0)
    return [face(c) for c in caps]


def depth(v):
    try:
        return int(v.split()[0])
    except (ValueError, IndexError):
        return None


def err(v):
    try:
        return int(v.split()[1])
    except (ValueError, IndexError):
        return None


def verdict(reads):
    """-> (verdict, d1, d2). SENSITIVE+LINEAR iff both +2000 B steps cost frames
    and cost the SAME to within 5% -- one pool at a constant rate. INSENSITIVE
    iff neither step costs a frame, which is what a fixed array reads as."""
    a, b, c = (depth(reads[l]) for l in LADDER)
    if None in (a, b, c):
        return "<not readable>", None, None
    d1, d2 = a - b, b - c
    if d1 == 0 and d2 == 0:
        return "INSENSITIVE", d1, d2
    if d1 <= 0 or d2 <= 0:
        return "NON-MONOTONIC", d1, d2
    if abs(d1 - d2) > 0.05 * max(d1, d2):
        return "SENSITIVE, NOT LINEAR", d1, d2
    return "SENSITIVE+LINEAR", d1, d2


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
    # ⚠️ THE THREE LADDER ROWS ALWAYS COME BACK, whatever --only says. Every
    # verdict in this probe -- including the REFERENCE precondition that gates
    # whether anything else is readable -- is computed from the ladder, so a
    # --only that dropped part of it would not scope the run, it would make the
    # run refuse. `ONLY=himem` did exactly that before this line existed.
    have = {c[0] for c in sel}
    sel = [c for c in CASES if c[0] in set(LADDER) | have]

    reads = {}
    for side, kw in list(SIDES.items()) + [("zb", dict(machine=args.zb_machine,
                                                       boot=8.0, reset=("NEW",)))]:
        reads[side] = dict(zip([c[0] for c in sel],
                               run(kw["machine"], kw["boot"], kw["reset"], sel)))

    sides = ["vg8020", "cf3300", "zb"]
    blank = sorted({f"{s}/{lab}" for s in sides for lab, v in reads[s].items()
                    if v == "<NO OUTPUT>"})
    if blank:
        print(f"INSTRUMENT FAULT: no reading on {blank} -- no verdict. "
              f"⚠️ Check the CLEAR/ON ERROR order first (see the docstring): "
              f"CLEAR resets the error vector and the overflow then goes untrapped.")
        return 2

    w = max(len(l) for l, _, _ in CASES)
    print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>10}" for s in sides) + "   statement")
    for lab, clr, why in sel:
        print(f"{lab:<{w}}  " + "  ".join(f"{reads[s][lab]:>10}" for s in sides)
              + f"   {clr or '(none)':<18} {why}")

    verdicts = {}
    print("\nbytes per frame, if the pool is shared:")
    for s in sides:
        v, d1, d2 = verdict(reads[s])
        verdicts[s] = v
        if d1 is None:
            print(f"  {s:<8} {v}")
            continue
        f1 = f"{STEP / d1:.1f}" if d1 else "--"
        f2 = f"{STEP / d2:.1f}" if d2 else "--"
        print(f"  {s:<8} +{STEP} B costs {d1:>5} frames ({f1:>4} B/frame), "
              f"next +{STEP} costs {d2:>5} ({f2:>4} B/frame)   {v}")

    bad = []

    # --- preconditions, read BEFORE any zerobas verdict is a finding ---------
    for s in ("vg8020", "cf3300"):
        if verdicts[s] != REF_EXPECT:
            print(f"⚠️ THE REFERENCE DID NOT REPRODUCE ITS OWN MODEL: {s} reads "
                  f"{verdicts[s]!r}, not {REF_EXPECT!r}. The oracle or the harness "
                  f"moved since docs/spec-basic-trapsvc.md §11 -- no row in this "
                  f"run is readable.")
            return 1
    errs = {(s, lab): err(reads[s][lab]) for s in sides for lab in reads[s]}
    wrong = sorted(k for k, v in errs.items() if v != 7)
    if wrong:
        print(f"⚠️ A ROW STOPPED ON SOMETHING OTHER THAN ERR 7 (Out of memory): "
              f"{wrong}. The recursion did not end the way this probe reads it.")
        return 1

    # --- 🎯 the prediction a fixed array cannot make, checked where it means
    #     something: BETWEEN the references, with the ceiling pinned ----------
    if "c.himem" in reads["vg8020"]:
        hv, hc = reads["vg8020"]["c.himem"], reads["cf3300"]["c.himem"]
        if hv == hc:
            print(f"\nc.himem: the two references agree EXACTLY ({hv}) with HIMEM "
                  f"pinned -- one HIMEM-bounded pool, not an array.")
        else:
            bad.append("c.himem/refs")
            print(f"\n🔴 c.himem: the references DISAGREE ({hv} vs {hc}) with HIMEM "
                  f"pinned. §11's sharpest row has moved.")
        # ⚠️ `.get`, not `[...]`: c.base is not force-selected the way the ladder
        # is, so `--only himem` has no baseline to compare against. A missing
        # baseline skips this half rather than crashing the run -- the
        # reference-vs-reference check above does not depend on it.
        for s in sides:
            db, dh = depth(reads[s].get("c.base", "")), depth(reads[s]["c.himem"])
            if dh is not None and db is not None and dh >= db and verdicts[s] != "INSENSITIVE":
                bad.append(f"c.himem/{s}")
                print(f"🔴 {s}: lowering HIMEM did not cost depth ({db} -> {dh}) "
                      f"although the machine is {verdicts[s]}.")

    # --- zerobas's own verdict ------------------------------------------------
    want = PINNED.get("zb", REF_EXPECT)
    if verdicts["zb"] != want:
        bad.append("zb")
        print(f"\n🔴 zerobas reads {verdicts['zb']!r}, expected {want!r}.")
        print("  The control-frame-pool arc made this row AGREE; if it has gone "
              "back to INSENSITIVE, the pool is not being reset (clear_vars -> "
              "ctl_reset) or CTLTOP is not tracking POOLSIZE/HIMEM.")
    else:
        print(f"\nzerobas: {verdicts['zb']} -- agrees with both references on the "
              f"MODEL (the depth and the rate are per-machine, and ungated).")

    print(f"\nrows {len(sel)}  red {len(bad)}")
    print("STACKPOOL: PASS" if not bad else f"STACKPOOL: RED ({len(bad)})")
    return 1 if (bad and args.gate) else 0


if __name__ == "__main__":
    sys.exit(main())
