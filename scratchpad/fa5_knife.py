#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""K-FA5, RE-RUN -- what does cutting the FIELD abort read now?

TODO (filed 2026-08-09 by D-STMTPEND, docs/spec-basic-stmtpend.md §6.3): K-FA5's
falsifiability premise went stale and five comments were reworded to say so, but
**the knife was never re-run**. This is that run.

THE PREMISE THAT DIED. `basic/field.asm`'s `tgt_parse_fld` aborts a failed array
resolve with `jp nz,fp_runtime_error`, and both that comment and
`basic_probe_fldary.py`'s `d.aryoor` row argued the abort is falsifiable BECAUSE
"exec_stmt CLEARS FPERR at the statement boundary ... so cutting this makes
`FIELD..A$(9)` print OK". D-STMTPEND turned the boundary into a READER: it now
consults the pending cell and raises. So a cut no longer falls through to
silence -- it falls through to a report from somewhere else.

🎯 WHAT THIS RUN IS FOR, AND WHAT IT IS NOT. It is NOT "does the row still go
red" -- that is the cheap half and either answer is publishable. It is **which
mechanism now reddens it**, because the reworded comments claim the check still
earns its place for a DIFFERENT reason: it raises BEFORE `ex_field`'s side
effects, which the boundary is by construction too late for. That claim predicts
something specific and testable: with the abort cut, the row should still report
an error, but the FIELD's side effects should have happened first.

So the run reads two things, not one:

    d.aryoor      the error face -- does it still report, and with what?
    s.fld*        the side-effect faces -- did the cut let a partial FIELD land?

⚠️ A row going red is NOT evidence for the new premise on its own: the boundary
raising and the abort raising look identical in an error-only row. The rows that
separate them are the ones that read what the FIELD TABLE holds.

🔴 ROM-HASHED ROUND THE PLANT (D-KNIFEROM2): a knife that silently did not build
reports "0 rows moved", which is what a legitimately-inert arm looks like too.

    python3 scratchpad/fa5_knife.py
"""
from __future__ import annotations

import atexit
import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.chdir(ROOT)
sys.path.insert(0, HERE)
import knife_guard                                                # noqa: E402

TMP = "scratchpad/fa5_knife"
FLD = "basic/field.asm"
GATE = "probes/basic/basic_probe_fldary.py"

ANCHOR = "                jp      nz,fp_runtime_error ; FPERR already mapped by\n"
CUT = "                                            ; K-FA5 CUT: abort removed\n"

# 🔬 ARM 2 -- REACHABILITY, because arm 1 answering "nothing moved" has TWO
# causes and they are not the same finding: the abort could be unobservable, or
# the site could never be REACHED. `tgt_parse`'s own header says "a failed array
# resolve does NOT return (spec §5.3)", which would make this `jp nz` dead for
# exactly the case the rows exercise. Removing a branch cannot tell those apart;
# pointing it at a DISTINGUISHABLE error can (the D-NGRAM18b technique). If the
# rows still do not move with an unconditional ERR 5 planted here, the site is
# not reached -- one build, one run, unambiguous.
#
# 🔴 IT WAS NOT UNAMBIGUOUS, AND THE RESULT SAYS SO. Arm 2 moved 14 of 16, and
# the ONE row that held was `d.aryoor3` -- not because the site is unreached
# there, but because that row TRAPS the error and reads `LEN`, so ERR 5 and
# ERR 9 give it the identical reading. A row built to be blind to the error's
# identity is blind to this arm too. What arm 2 does establish is the opposite
# of the header-comment story: `d.aryoor` MOVED, so for a single out-of-range
# target control DOES return to this `jp nz`, and `tgt_parse`'s "a failed array
# resolve does not return" describes some other failure mode.
CUT2 = ("                ld      a,5                 ; K-FA5b: DISTINGUISHABLE\n"
        "                jp      raise_error         ; ...and UNCONDITIONAL\n")

ROW = re.compile(r"^\s*(?:PASS|FAIL|DIFF|ok)\s+(\S+)", re.M)


def run_gate(tag):
    log = f"{TMP}/{tag}.out"
    with open(log, "w") as fh:
        rc = subprocess.call([sys.executable, GATE, "--gate"],
                             stdout=fh, stderr=subprocess.STDOUT)
    return rc, open(log, encoding="utf-8", errors="replace").read(), log


def rows_of(txt):
    """label -> the whole reported line, for a before/after diff by ROW."""
    out = {}
    for ln in txt.splitlines():
        m = re.match(r"\s*(PASS|FAIL|DIFF|ok|🔴)\s+(\S+)\s*(.*)", ln)
        if m:
            out[m.group(2)] = ln.strip()
    return out


def main():
    os.makedirs(TMP, exist_ok=True)
    src = open(FLD).read()
    if src.count(ANCHOR) != 1:
        print(f"INSTRUMENT FAULT: the anchor occurs {src.count(ANCHOR)} time(s) "
              f"in {FLD}, not once -- the knife would cut nothing and its red "
              f"arm would pass by never firing.")
        return 2
    digest = hashlib.sha256(src.encode()).hexdigest()

    def restore():
        open(FLD, "w").write(src)
        assert hashlib.sha256(open(FLD).read().encode()).hexdigest() == digest
        print(f"  restored {FLD} byte-identically")
    atexit.register(restore)

    print("=== baseline (rebuild first: a previous restore leaves build/ knifed)")
    _m, _a, brc = knife_guard.build(f"{TMP}/base_build.log", None)
    if brc:
        print(f"INSTRUMENT FAULT: the clean tree does not build ({TMP}/base_build.log)")
        return 2
    print(f"  ROM {knife_guard.hashes()}")
    rc0, txt0, log0 = run_gate("base")
    before = rows_of(txt0)
    print(f"  fldary rc={rc0}, {len(before)} row(s) read   {log0}")
    if rc0:
        print("INSTRUMENT FAULT: the gate is red BEFORE the cut.")
        return 2

    arm2 = "--reach" in sys.argv
    if arm2:
        print("\n=== K-FA5b: the same site made an UNCONDITIONAL, DISTINGUISHABLE"
              " ERR 5 -- a reachability probe, not an abort probe")
    else:
        print("\n=== K-FA5: tgt_parse_fld's `jp nz,fp_runtime_error` removed")
    open(FLD, "w").write(src.replace(ANCHOR, CUT2 if arm2 else CUT, 1))
    h_before = knife_guard.hashes()
    moved, h_after, brc = knife_guard.build(f"{TMP}/cut_build.log", h_before)
    if brc:
        print(f"INSTRUMENT FAULT: the KNIFED tree does not build "
              f"({TMP}/cut_build.log) -- measured nothing.")
        return 2
    print(knife_guard.report("K-FA5", moved, h_before, h_after))
    if not moved:
        print("INSTRUMENT FAULT: the ROM did not change -- the cut did not take.")
        return 2
    rc1, txt1, log1 = run_gate("cut")
    after = rows_of(txt1)
    print(f"  fldary rc={rc1}   {log1}")

    print("\n=== rows that MOVED")
    movedrows = [k for k in before if before[k] != after.get(k, "<absent>")]
    if not movedrows:
        print("  none -- the cut is INVISIBLE to this row set, which is itself")
        print("  the answer: the abort's removal is not observable here.")
    for k in movedrows:
        print(f"  {k}")
        print(f"     before: {before[k]}")
        print(f"     after:  {after.get(k, '<absent>')}")
    print(f"\n{len(movedrows)} row(s) moved of {len(before)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
