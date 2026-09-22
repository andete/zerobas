#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ALIASSCOPE -- is the 416 B overlap the MECHANISM, or only a neighbour?

`aliasbite_probe.py` established the EFFECT: a `KILL` between two reads of an
open main channel truncates that channel (second `INPUT$(4,#1)` returns ""). It
does NOT establish WHY. The 416 B overlap is the obvious candidate and an
obvious candidate is not a cause [[a-filed-guess-at-a-cause-is-not-a-cause]].

🔴 THE FIRST CUT'S DISCRIMINATOR WAS VOID, AND SAYING SO IS THE POINT. It split
main's `FSECTOR_BUF` (`$E5C0..$E7BF`) at the top of disk's `WBUF` and called the
remainder "main DATA only -- disk's map does not reach here". **It does.**
`docs/ram-map.md` declares **23 `disk` cells inside that buffer, spanning
`$E5C0..$E7B1`** -- the `$0030` handler's register stashes, `CALSLT_HL`, the
`RDBLK`/`FREAD_OFF` state, the hook bodies `WA_SEG`, `CONOUT_CHAR`, `PG_SV_A8`.
TODO.md's own same-address item records the count. A control region assumed
clean, and contradicted by a line in the item being worked, is not a control
[[a-coverage-row-whose-geometry-cannot-reach-the-case]].

🎯 SO THE TWO WINDOWS DO NOT SEPARATE "SHARED" FROM "MAIN'S OWN" -- there is no
main's-own left. What they separate is WHICH disk structure is doing the
writing, which is still worth having:

    UNDER_WBUF   $E5C0..$E75F   main DATA under disk's 512 B META buffer
    UNDER_CELLS  $E760..$E7BF   main DATA under ~20 individually declared cells

A verb that hits only UNDER_WBUF is clobbering main's buffer with a sector; one
that hits both is also stepping on the per-crossing scratch, which is written
on EVERY crossing rather than only by verbs that mount. Neither region being
touched would mean the truncation has another cause and the overlap is a
bystander -- the outcome that would save a large slice of work.

⚠️ THE CONTROL IS THE SAME PROGRAM WITHOUT THE `KILL`. Without it, "writes
happened in the window" says nothing: main's own file code writes its own
buffer, and that is not the finding.

📏 The counts are taken only between two POKE phase markers that BRACKET the
verb, so main's own reads before and after are excluded by construction.

🔴 AND THE FOOTPRINT DOES NOT PREDICT THE OUTCOME -- MEASURED, NOT ASSUMED.
`OPEN"Y.DAT"FOR INPUT AS#2` produces the SAME counts as `NAME` (832 / 192) and
the open channel SURVIVES it. So a reading here says what a verb TOUCHES; it
does not say whether the channel breaks. Pair it with aliasbite_probe.py's
extent sweep, which reads the outcome, and do not infer one from the other.

⚠️ `run_gap`, not `cap_gap` -- see aliasbite_probe.py's note and
tests/test_capture_budget.py.

    python3 -u scratchpad/aliasscope_probe.py [--selftest]
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp  # noqa: E402,F401  -- module level, sets tempfile.tempdir
import omsx_repl  # noqa: E402

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
SRC_DSK = os.path.join(ROOT, "disk", "test720.dsk")

# The two windows, from docs/ram-map.md. ⚠️ BOTH are shared with disk -- see the
# docstring. Neither is main's own, and the second is NOT a clean control.
OVERLAP = (0xE5C0, 0xE75F)          # main FSECTOR_BUF ∩ disk WBUF
BEYOND = (0xE760, 0xE7BF)           # main FSECTOR_BUF ∩ ~20 declared disk cells
# 🔴 NOT $D000, AND THE COUNTS THIS PROBE PUBLISHED BEFORE 2026-09-23 WERE
# LOWER BOUNDS BECAUSE OF IT. The window is gated on `$::ph == 1`, and THE
# MACHINE writes $D000 32 times per disk program (15/240 alternating,
# scratchpad/cellpriv.out) -- each one closed the gate early. $CFFE took none of
# them (scratchpad/findquiet.out), and every $xx00 boundary took all 32, so the
# round number was the worst available choice.
# ⚠️ AND THE CELL IS RE-VERIFIED IN EVERY RUN rather than trusted: the callback
# logs each value written, and a value that is not 1 or 2 REFUSES the run
# [[a-marker-cell-is-a-claim-nobody-else-writes-it]].
PHASE = 0xCFFE                      # measured quiet; verified again per run

BODY = [
    # CLEAR puts BASIC's ceiling well below the marker cell.
    "1 CLEAR 200,&HBFFF",
    "5 MAXFILES=2",
    '10 OPEN"Y.DAT"FOR OUTPUT AS#1',
    '15 PRINT#1,"X"',
    "17 CLOSE#1",
    '20 OPEN"Z.DAT"FOR OUTPUT AS#1',
    '30 PRINT#1,"ABCDEFGHIJKLMNOP"',
    "40 CLOSE#1",
    "45 ON ERROR GOTO 99",
    '50 OPEN"Z.DAT"FOR INPUT AS#1',
    "60 A$=INPUT$(4,#1)",
    "65 POKE&HCFFE,1",                 # window OPENS
]
TAIL = [
    "75 POKE&HCFFE,2",                 # window CLOSES
    "80 B$=INPUT$(4,#1)",
    "85 CLOSE#1",
    "95 PRINTCHR$(91);A$;B$;CHR$(93):END",
    '99 PRINTCHR$(91);"E";ERR;CHR$(93)',
    "RUN",
]
# 🔴 A CLASS IS NOT ONE VERB. `KILL` alone would license "KILL corrupts an open
# channel"; the claim worth making is about any disk-ROM verb that MOUNTS, so
# the sweep names them [[a-shared-tail-is-not-a-decision]]. Both print nothing,
# which keeps the screen the fence is read from undisturbed.
# ⚠️ `OPEN-IN` IS HERE BECAUSE THE EXTENT SWEEP REFUTED THE OBVIOUS STORY. A
# second `OPEN` on another channel does NOT truncate the first, so "main's own
# engine reuses FSECTOR_BUF for any file operation" is false. This arm asks the
# question that separates the remaining explanations: does main's own `OPEN`
# write into that buffer AT ALL? If it writes and stays clean, writing is not
# sufficient and the difference lies elsewhere.
VERBS = [("KILL", ['70 KILL"Y.DAT"']),
         ("NAME", ['70 NAME"Y.DAT"AS"W.DAT"']),
         ("DSKF", ["70 X=DSKF(0)"]),
         ("OPEN-IN", ['70 OPEN"Y.DAT"FOR INPUT AS#2', "72 CLOSE#2"])]


def prologue(log):
    """Tcl: count writes to each window, but only while the phase cell reads 1.

    The phase gate is what makes the count attributable. Main's own file code
    writes its own buffer on every read, so an ungated count would be dominated
    by exactly the traffic that is NOT the subject."""
    w = (f'set ::sf [open "{log}" w]\n'
         f'set ::ph 0\n'
         f'debug set_watchpoint write_mem {PHASE} {{}} '
         f'{{ set ::ph [debug read memory {PHASE}];'
         f'  puts $::sf "PH$::ph"; flush $::sf }}\n')
    for name, (lo, hi) in (("OVERLAP", OVERLAP), ("BEYOND", BEYOND)):
        w += (f'debug set_watchpoint write_mem {{{lo} {hi}}} {{}} '
              f'{{ if {{$::ph == 1}} {{ puts $::sf "{name}"; flush $::sf }} }}\n')
    return w


def counts(path):
    """{OVERLAP, BEYOND} counts, or None when the phase cell was not private.

    🔴 THE SECOND RETURN IS THE POINT. Every write to the phase cell is logged,
    and a value other than the two the program pokes means SOMEONE ELSE wrote
    it -- which silently closes the gate and under-counts. That is exactly what
    $D000 did, so the claim is re-earned per run instead of written down once."""
    try:
        txt = open(path).read()
    except OSError:
        return None
    stray = [v for v in re.findall(r"PH(\d+)", txt) if v not in ("1", "2")]
    if stray:
        print(f"    🔴 phase cell NOT private: {len(stray)} foreign write(s), "
              f"values {sorted(set(stray))[:6]}")
        return None
    return {n: txt.count(n) for n in ("OVERLAP", "BEYOND")}


def verdict(ctl, sub):
    """Named before the run, so the outcome cannot be chosen after it."""
    if ctl is None or sub is None:
        return "REFUSED (a run produced no log)"
    if ctl["OVERLAP"] or ctl["BEYOND"]:
        return (f"INSTRUMENT FAULT: the CONTROL window is not quiet "
                f"({ctl}) -- the bracket does not isolate the verb, so no "
                f"count in the subject can be attributed to it")
    if not sub["OVERLAP"] and not sub["BEYOND"]:
        return ("NEITHER — the verb writes nowhere in main's data buffer, so "
                "the overlap is a BYSTANDER and the truncation has another "
                "cause; do not aim a relocation at it")
    if sub["OVERLAP"] and not sub["BEYOND"]:
        return (f"WBUF ONLY — {sub['OVERLAP']} write(s) in $E5C0..$E75F and "
                f"ZERO above: the verb overwrites main's open sector with its "
                f"own META buffer, and touches no per-crossing scratch")
    if sub["OVERLAP"] and sub["BEYOND"]:
        return (f"WBUF *AND* THE DECLARED CELLS — {sub['OVERLAP']} write(s) in "
                f"$E5C0..$E75F and {sub['BEYOND']} in $E760..$E7BF, which holds "
                f"~20 declared disk cells: main's buffer is hit by a sector AND "
                f"by per-crossing scratch, so a mount is not the only exposure")
    return (f"CELLS ONLY — {sub['BEYOND']} write(s) in $E760..$E7BF and none "
            f"below: only the per-crossing scratch, no sector")


def selftest():
    fails = 0

    def arm(label, cond):
        nonlocal fails
        if not cond:
            print(f"  selftest: FAIL {label}")
            fails += 1

    quiet = {"OVERLAP": 0, "BEYOND": 0}
    arm("WBUF window only -> WBUF ONLY",
        verdict(quiet, {"OVERLAP": 7, "BEYOND": 0}).startswith("WBUF ONLY"))
    arm("nothing anywhere -> NEITHER",
        verdict(quiet, quiet).startswith("NEITHER"))
    arm("both windows -> WBUF *AND* THE DECLARED CELLS",
        verdict(quiet, {"OVERLAP": 7, "BEYOND": 3}).startswith("WBUF *AND*"))
    arm("upper window only -> CELLS ONLY",
        verdict(quiet, {"OVERLAP": 0, "BEYOND": 3}).startswith("CELLS ONLY"))
    # 🔴 THE ARM THAT KEEPS A BROKEN BRACKET FROM INDICTING THE ROM: if the
    # CONTROL window already has traffic, the bracket is not isolating the verb
    # and no count in the subject means anything.
    arm("NEGATIVE: a noisy CONTROL is an INSTRUMENT FAULT, not a finding",
        verdict({"OVERLAP": 2, "BEYOND": 0},
                {"OVERLAP": 7, "BEYOND": 0}).startswith("INSTRUMENT FAULT"))
    arm("NEGATIVE: a missing run refuses",
        verdict(None, quiet).startswith("REFUSED"))
    # and the counter itself: it must be able to see a hit AND to report none.
    p = tempfile.mkstemp(suffix=".log")[1]
    # 🔴 THE ARM FOR THE REFUSAL THAT WAS ADDED AFTER $D000 WAS CAUGHT: a log
    # carrying a phase value the program never poked must REFUSE, not count.
    open(p, "w").write("PH1\nOVERLAP\nPH15\nOVERLAP\nPH2\n")
    arm("NEGATIVE: a foreign write to the phase cell REFUSES the run",
        counts(p) is None)
    open(p, "w").write("PH1\nOVERLAP\nOVERLAP\nPH2\nBEYOND\n")
    arm("a log with only the program's own phase values counts normally",
        counts(p) == {"OVERLAP": 2, "BEYOND": 1})
    open(p, "w").write("OVERLAP\nOVERLAP\nBEYOND\n")
    arm("the counter reads a log", counts(p) == {"OVERLAP": 2, "BEYOND": 1})
    open(p, "w").write("")
    arm("NEGATIVE: an empty log counts zero, it does not crash",
        counts(p) == {"OVERLAP": 0, "BEYOND": 0})
    arm("NEGATIVE: a missing log is None, not a zero count",
        counts(os.path.join(os.path.dirname(p), "no-such-file.log")) is None)
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def run(label, prog):
    tmp = tempfile.mkstemp(suffix=".dsk")[1]
    shutil.copyfile(SRC_DSK, tmp)      # never write the tracked fixture
    log = probe_tmp.tmp(f"aliasscope_{label}.log")
    omsx_repl.run_cases(ZB, [(label, prog)], batch=False, reset=(),
                        boot=8.0, step=3.0, cap_gap=2.5, run_gap=60.0,
                        timeout=900.0, diska=tmp, prologue=(prologue(log),))
    c = counts(log)
    print(f"  {label}: {c}")
    return c


def main(argv):
    print("D-ALIASSCOPE: is the 416 B overlap the mechanism, or a neighbour?\n")
    if "--selftest" in argv:
        return 1 if selftest() else 0
    ctl = run("CONTROL  no-verb", BODY + TAIL)
    print()
    for name, lines in VERBS:
        sub = run(f"SUBJECT  {name}", BODY + lines + TAIL)
        print(f"  VERDICT {name}: {verdict(ctl, sub)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
