#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""What error class does EVERY channel-taking verb answer to a channel number the
channel layer REJECTS?  (D-BADFNUM, docs/spec-basic-badfnum-channel-class.md)

TODO.md filed THREE rows -- `PRINT #2`, `INPUT #2`, `PRINT #0` -- and warned that
they do not generalise, because channel 0 and channel 2 earn different reference
codes.  That warning was right and it was the smaller half.  A static read of
basic/ said `fch_valid` had NINE call sites routing their reject to SIX different
places (`load_error`, a silent no-op, ERR 52, ERR 2 twice over, and a silent `0`
out of the evaluator), so the filed rows walked 2 of 9 sites and 1 of 6
dispositions.

THE DENOMINATOR IS THEREFORE 12 VERBS x 5 CHANNEL CLASSES, and this battery types
all 60 cells on both machines rather than sampling them.

  🔴 SAMPLING WAS TRIED FIRST AND THE SWEEP REFUTED IT.  A first battery took the
  last three classes on three verbs (`prw`/`get`/`lof`) and read a perfectly
  uniform rule -- 16 -> BFN, 256/-1 -> IFC.  But the one verb already KNOWN to
  follow a different rule at channel 0 (`OPEN`, which answers 52 where the other
  eleven answer 59) was not among the three, and it is the one that breaks the
  pattern: `OPEN … AS #256` is IFC on the reference and BFN on zerobas.  Sampling
  would have shipped that cell wrong and called the grid closed.  At ~14 s for 37
  boots there was never a reason to sample (memory: gpfi-wrongmode-grid-slice --
  a grid sampled at three of its seven rows is not a denominator).

THE MEASURED REFERENCE RULE (CF-3300), which is what this gate holds:

  D != 0 (>255 or negative)  ERR 5   illegal function call  -- ALL 12 verbs
  channel 0                  ERR 59  file not open          -- except CLOSE (no-op)
                                                              and OPEN (ERR 52)
  1 .. MAXF                  proceeds to the mode checks
  channel > MAXF             ERR 52  bad file number        -- ALL 12 verbs

CONTROLS -- rows that MUST agree, so a red row elsewhere is attributable to the
subject rather than to the harness:
  * `ctl_syntax`      a misspelled keyword -> `Syntax error`.  If this comes back
    clean the harness is not typing and every reading here is worthless.
  * `ctl_ch1_open`    `OPEN "HI.TXT" FOR INPUT AS #1 : PRINT LOF(1)` -> 26 both.
    A LEGAL channel still works -- proves the battery is not simply breaking
    every channel it touches, which is how a "fix" that raised unconditionally
    would otherwise have turned this whole grid green.
  * `ctl_pr1_closed`  `PRINT #1,"X"` -> `file not open` both.  In range, not open:
    the cell NEXT DOOR to the subject, green since D-NOTOPEN.
  * `ctl_mf2_ch2`     `MAXFILES=2 : PRINT #2,"X"` -> `file not open` both.  THE
    RULE-SEPARATING ROW: it pins the boundary to MAXF rather than to the constant
    2.  Without it "channel 2 is bad" and "channel 2 is past the ceiling" are the
    same reading, and a fix that hard-coded 2 would pass the entire grid.
  * `trap_lof1`       `A=LOF(1)` under an armed handler -> 59 both, GREEN BEFORE
    THIS SLICE AS WELL AS AFTER.  Without it a `trap_lof0` reading `0` cannot
    tell "nothing was raised" from "this probe cannot read a trap at all".

⚠️ `Type mismatch` and `Overflow` are in ERR_CLASSES FROM THE START.  In the
scratch battery they were absent, so four rows read `None` -- and `None` is also
what a row reads when NOTHING WENT WRONG.  They were resolved by reading the
screens, not by trusting the sentinel (memory: appmiss-slice -- a sentinel that
also means "no reading" is not a measurement).

APPARATUS inherited wholesale from diskbasic_probe_lof.py: measured screen
geometry (CF-3300 Disk BASIC boots SCREEN 1 at linlen=29 with a left margin of 2),
the 14.0 s cadence, and the echo guard.  Every case is at most 4 typed lines,
well inside the guard's "nothing scrolls off" assumption.

CLEAN-ROOM: black-box only -- typed BASIC in, screen out.  No reference ROM is
read or disassembled.
DISK SAFETY: every case runs on a /tmp COPY of disk/test720.dsk.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import argparse
import concurrent.futures as cf

from diskbasic_probe_lof import ERR_CLASSES, run_case

# The scratch battery's four `None` readings were `Type mismatch` and `Overflow`.
# Registered here so no row of this grid can ever classify as None again.
ERR_CLASSES.setdefault("TMIS", ("Type mismatch",))
ERR_CLASSES.setdefault("OVF", ("overflow",))

# The twelve channel-taking verbs, as a one-line statement with `{C}` where the
# channel number goes.  `:PRINT 7` is appended wherever a NON-error outcome is
# reachable, so "no error" reads as the value 7 -- a positive reading, not an
# absent one.  EOF/LOF print their own value instead, which is exactly how their
# silent-`0` defect was visible at all.
VERBS = [
    ("prw", 'PRINT #{C},"X"'),
    ("pru", 'PRINT #{C},USING "!";"X"'),
    ("inp", 'INPUT #{C},A$'),
    ("lin", 'LINE INPUT #{C},A$'),
    ("clo", 'CLOSE #{C}:PRINT 7'),
    ("opn", 'OPEN "HI.TXT" FOR INPUT AS #{C}:PRINT 7'),
    ("fld", 'FIELD #{C},10 AS A$:PRINT 7'),
    ("get", 'GET #{C},1:PRINT 7'),
    ("put", 'PUT #{C},1:PRINT 7'),
    ("ind", 'A$=INPUT$(3,#{C}):PRINT 7'),
    ("eof", 'PRINT EOF({C})'),
    ("lof", 'PRINT LOF({C})'),
]

#   c0    the channel layer's first reject
#   c2    > MAXF (MAXFILES defaults to 1), still <= FCH_CEIL
#   c16   > MAXF *and* above the measured reference ceiling of 15
#   c256  D != 0.  Six of the nine sites used to truncate this to E = 0 silently.
#   cneg  through eval_chan's int coercion first
#   ctm   a STRING channel expression -> `Type mismatch`, uniformly, all 12 verbs.
#
# 🔴 `ctm` IS HERE BECAUSE SAMPLING IT COST A REGRESSION.  It began as three edge
# cells (`PRINT #A$`, `INPUT #A$`, `LOF(A$)`) rather than a class, and `LOF(A$)`
# was among them ONLY because it already agreed on both machines.  The first cut
# of `fch_check` broke exactly that row -- a type mismatch hard-zeroes the channel
# to 0, so a routine that answers ERR 59 to channel 0 answers it here too -- and
# the other nine verbs of the column had never been typed at all.  A control row
# earned its keep by going red, one axis over from the axis this slice was
# already sweeping deliberately.
CLASSES = [("c0", "0"), ("c2", "2"), ("c16", "16"),
           ("c256", "256"), ("cneg", "-1"), ("ctm", "A$")]

CASES = [
    ("ctl_syntax",     ['OPEM "HI.TXT" FOR INPUT AS #1']),
    ("ctl_ch1_open",   ['OPEN "HI.TXT" FOR INPUT AS #1:PRINT LOF(1)']),
    ("ctl_pr1_closed", ['PRINT #1,"X"']),
    ("ctl_mf2_ch2",    ['MAXFILES=2:PRINT #2,"X"']),
]
_TPL = dict(VERBS)
for _cn, _cv in CLASSES:
    for _vn, _t in VERBS:
        CASES.append((f"{_vn}_{_cn}", [_t.format(C=_cv)]))

# --- TRAPPABILITY, the semantics half.  `load_error` PRINTED AND RETURNED: the
# program kept running and an armed handler never saw it.  A real ERR 5/52/59
# aborts or traps.  The handler prints the code, so `0` reads as "no error was
# raised at all" and the three outcomes stay distinguishable.
for _lbl, _stmt in [("trap_prw0", 'PRINT #0,"X"'), ("trap_prw2", 'PRINT #2,"X"'),
                    ("trap_prw256", 'PRINT #256,"X"'),
                    ("trap_get2", "GET #2,1"), ("trap_clo2", "CLOSE #2"),
                    ("trap_lof0", "A=LOF(0)"), ("trap_lof2", "A=LOF(2)"),
                    ("trap_lof1", "A=LOF(1)")]:
    CASES.append((_lbl, ["10 ON ERROR GOTO 100", f"20 {_stmt}",
                         "100 PRINT ERR", "RUN"]))

# --- The EDGE cells the slice TOUCHES.  A fix must not move a cell whose
# reference value is unknown, so these were measured BEFORE the design was fixed.
# The six that already agreed are here as controls: they are the rows that go red
# if fch_check starts rejecting something it should pass.
for _lbl, _line in [
        ("edge_flt_prw", 'PRINT #1.7,"X"'),      # float channel truncates to 1
        ("edge_flt_lof", "PRINT LOF(1.7)"),
        ("edge_ovf",     'PRINT #99999*99999,"X"'),  # eval_chan raises FIRST
        ("edge_c255",    'PRINT #255,"X"'),      # D=0, E=255, > MAXF
        ("edge_c1_eof",  "PRINT EOF(1)"),
        ("edge_mf2_clo", "MAXFILES=2:CLOSE #2:PRINT 7"),
        ("edge_mf2_lof", "MAXFILES=2:PRINT LOF(2)")]:
    CASES.append((_lbl, [_line]))
# (the three `#A$` edge cells that used to live here are now the full `ctm`
#  column above -- see the CLASSES comment for why that promotion happened)

# --- K0: the pair that keeps the DESIGN'S OWN JUSTIFICATION honest ------------
# fch_check_nz routes its ERR 52 through oo_fail_bfn, which CLEARS FCH_MODE. That
# is OPEN's own cleanup ("the provisional mode must not survive a failed OPEN"),
# and the spec argues it is harmless for the eight non-OPEN callers because every
# reader of FCH_MODE is preceded by fch_select, which re-stamps the mirror. If
# that argument is wrong, a TRAPPED `PRINT #2` sitting between an OPEN and a write
# on a DIFFERENT, legitimately-open channel corrupts the second write.
#
# ⚠️ THE VERDICT IS THE ON-DISK DIRECTORY, NOT A SCREEN READING -- and it needs
# BOTH columns. The first cut of this row read DIR=7 on subject and control alike
# and looked like a pass, but both had fallen into the handler and printed
# `RESUME without error`, so "7 both" could not tell "the trap fired and the write
# survived" from "line 20 did nothing at all". The handler now RECORDS the code
# and the program ENDs, so `k0_trapped` reads 52 (the trap fired) with DIR 7 (the
# other channel's write landed) while `k0_control` reads 0 with DIR 7.
# Memory: gpfi-wrongmode-grid-slice -- aim a knife at your own justification.
CASES.append(("k0_trapped",
              ['10 ON ERROR GOTO 100:OPEN "ZQ.DAT" FOR OUTPUT AS #1',
               '20 PRINT #2,"BAD"',
               '30 PRINT #1,"GOOD":CLOSE:PRINT E:END',
               "100 E=ERR:RESUME NEXT", "RUN"], "ZQ      DAT"))
CASES.append(("k0_control",
              ['10 ON ERROR GOTO 100:OPEN "ZQ.DAT" FOR OUTPUT AS #1',
               '30 PRINT #1,"GOOD":CLOSE:PRINT E:END',
               "100 E=ERR:RESUME NEXT", "RUN"], "ZQ      DAT"))

# The directory oracle for the two K0 rows -- "GOOD" + CRLF + Ctrl-Z = 7 bytes.
# A row agrees only if BOTH its columns agree (memory: appmiss-slice, where this
# column was measured, printed and never compared).
DIR_EXPECT: dict = {"k0_trapped": 7, "k0_control": 7}

# --- ORACLE LOCK ------------------------------------------------------------
# The reference's MEASURED answer per row, recorded 2026-07-31.  A change here is
# ORACLE DRIFT (a different machine/ROM/disk), not a zerobas result, and fails the
# run on its own.  Built from the rule in the module docstring rather than typed
# out 60 times -- the exceptions are listed explicitly BELOW the rule, so a reader
# can see that there are exactly four of them.
REF_EXPECT: dict = {
    "ctl_syntax": "SYNTAX", "ctl_ch1_open": 26,
    "ctl_pr1_closed": "FNO", "ctl_mf2_ch2": "FNO",
    "trap_prw0": 59, "trap_prw2": 52, "trap_prw256": 5,
    "trap_get2": 52, "trap_clo2": 52,
    "trap_lof0": 59, "trap_lof2": 52, "trap_lof1": 59,
    "edge_flt_prw": "FNO", "edge_flt_lof": "FNO", "edge_ovf": "OVF",
    "edge_c255": "BFN", "edge_c1_eof": "FNO",
    "edge_mf2_clo": 7, "edge_mf2_lof": "FNO",
    "k0_trapped": 52, "k0_control": 0,
}
for _cn, _ in CLASSES:
    for _vn, _ in VERBS:
        REF_EXPECT[f"{_vn}_{_cn}"] = {"c0": "FNO", "c2": "BFN", "c16": "BFN",
                                      "c256": "IFC", "cneg": "IFC",
                                      "ctm": "TMIS"}[_cn]
# The FOUR exceptions to the rule, each measured, each the reason a "one code per
# channel class" fix would be wrong. ⚠️ The `ctm` column has NONE -- CLOSE and OPEN
# answer `Type mismatch` there like everything else, so their channel-0 leniency
# does NOT extend to a string channel that merely hard-zeroes to 0.
REF_EXPECT["clo_c0"] = 7        # CLOSE is lenient about channel 0 -- and ONLY 0
REF_EXPECT["opn_c0"] = "BFN"    # OPEN answers 52 where all eleven others say 59
REF_EXPECT["opn_c2"] = "BFN"    # (52 either way, but for the OTHER reason)
REF_EXPECT["opn_c16"] = "BFN"

# --- GATE: divergences that are FILED AND EXPECTED, with the item owning each.
# Everything NOT listed here must MATCH the reference, and a row that starts
# diverging DIFFERENTLY still trips the gate (the value is part of the key).
#
# ⚠️ THIS LIST IS EMPTY, AND THAT IS AN ASSERTED STATE RATHER THAN AN ABSENT ONE.
# An allowlist that must keep matching is a control; one that only suppresses is
# rot (memory: deadcode-gate).  `--gate` fails if a label here is NOT diverging,
# so an entry cannot rot silently -- and with the dict empty that check is
# vacuous, which is exactly why the emptiness is stated here in words instead of
# being left for a reader to infer from a dict with no lines in it.
KNOWN_DIVERGE: dict = {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated case labels")
    ap.add_argument("--side", choices=("ref", "zb", "both"), default="both")
    ap.add_argument("--gate", action="store_true",
                    help="exit nonzero on any unfiled divergence or oracle drift")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    ap.add_argument("--line-delay", type=float, default=14.0)
    ap.add_argument("-v", "--verbose", action="store_true", help="print screens")
    args = ap.parse_args()

    # a case is (label, lines) or (label, lines, directory-name-to-read)
    cases = [(c[0], c[1], c[2] if len(c) > 2 else None) for c in CASES]
    if args.only:
        want = set(args.only.split(","))
        cases = [c for c in cases if c[0] in want]
    sides = ["ref", "zb"] if args.side == "both" else [args.side]

    jobs = [(s, lbl, lines, dn, args.line_delay)
            for lbl, lines, dn in cases for s in sides]
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        results = list(ex.map(lambda j: run_case(*j), jobs))

    got, dirs, screens = {}, {}, {}
    for side, label, value, rows, meta, dsz in results:
        got[(side, label)] = value
        dirs[(side, label)] = dsz
        screens[(side, label)] = (rows, meta)

    print(f"{'case':16} {'typed':36} {'ref':>9} {'zb':>9} {'dir':>9}  note")
    mangled = unfiled = drift = 0
    for lbl, lines, dn in cases:
        rv, zv = got.get(("ref", lbl)), got.get(("zb", lbl))
        rd, zd = dirs.get(("ref", lbl)), dirs.get(("zb", lbl))
        note = ""
        if rv == "MANGLED" or zv == "MANGLED":
            note, mangled = "!! MANGLED -- APPARATUS", mangled + 1
        elif "ref" in sides and lbl in REF_EXPECT and rv != REF_EXPECT[lbl]:
            note, drift = f"ORACLE DRIFT (recorded {REF_EXPECT[lbl]!r})", drift + 1
        elif "ref" in sides and lbl in DIR_EXPECT and rd != DIR_EXPECT[lbl]:
            note, drift = f"DIR ORACLE DRIFT (recorded {DIR_EXPECT[lbl]!r})", drift + 1
        elif rv != zv or (dn and rd != zd):
            # BOTH columns are in the verdict: a row agrees only if the screen
            # reading AND the directory agree (memory: appmiss-slice).
            if KNOWN_DIVERGE.get(lbl) == (rv, zv):
                note = "filed divergence"
            else:
                note, unfiled = "DIVERGE (UNFILED)", unfiled + 1
        dcol = "-" if not dn else (f"{rd}/{zd}" if rd != zd else str(rd))
        print(f"{lbl:16} {lines[-1][:36]:36} {str(rv):>9} {str(zv):>9} "
              f"{dcol:>9}  {note}")
        if args.verbose:
            for s in sides:
                rows, meta = screens.get((s, lbl), ([], ""))
                print(f"    [{s}] {meta}")
                for r in rows:
                    print(f"        | {r}")

    # every case must carry an oracle lock -- an unrecorded row cannot drift
    unlocked = [lbl for lbl, _l, _d in cases if lbl not in REF_EXPECT]
    print(f"\n{len(cases)} cases, {mangled} mangled, {drift} oracle drift, "
          f"{unfiled} unfiled divergence, {len(unlocked)} without an oracle lock")
    if unlocked:
        print(f"  no REF_EXPECT entry: {unlocked}")
    if args.gate:
        # a filed entry that has STOPPED diverging is rot -- fail on it too.
        stale = [lbl for lbl in KNOWN_DIVERGE
                 if got.get(("ref", lbl)) == got.get(("zb", lbl))]
        if stale:
            print(f"  STALE KNOWN_DIVERGE (no longer diverging): {stale}")
        return 1 if (mangled or drift or unfiled or unlocked or stale) else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
