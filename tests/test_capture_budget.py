#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CAPGAP -- WHICH KNOB BUYS A CASE ITS RUN->CAPTURE BUDGET.

Pure host Python: no emulator, no ROM. It reads the Tcl `_tcl` actually
generates and pins the one fact every caller has to know:

  * the capture fires at `run_gap` past RUN when one is given, and at `step`
    past RUN otherwise;
  * **`cap_gap` NEVER MOVES IT.** It is the gap AFTER the capture -- inter-case
    spacing and the scheduled exit -- and buys the case that owns it nothing
    (docs/spec-probe-budget.md S1).

🔴 WHY THIS FILE EXISTS, AND IT IS NOT THAT THE FACT WAS UNKNOWN. S1 of that
spec states it in bold, and `_tcl` repeats it in a comment beside the code. It
was still missed, because the two places that carry it are the two places a
CALLER never reads: the parameter list carries no docstring, and `cap_gap` is a
name that reads like "the gap before the capture". D-TWOFILE spent five wrong
diagnoses -- a hang, a silent abort, a dead screen -- on one probe that passed
`cap_gap=70.0` to buy a 4.4 s program some room and actually bought it 3.0 s,
so the capture landed mid-program and read a half-drawn screen as a defect.
An emulator-free row cannot go silent and does not need the fact restated in
prose, which is why the pin is here rather than in another comment.
[[apparatus-is-part-of-the-measurement]]
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "probes", "lib"))
import omsx_repl  # noqa: E402

fails = []


def check(label, got, want):
    if got != want:
        fails.append(f"{label}: got {got!r}, want {want!r}")
    print(f"  {'PASS' if got == want else 'FAIL'}  {label:<54} {got!r}")


CASES = [("c", ["10 PRINT 1", "RUN"])]
BOOT, STEP = 8.0, 3.0


def cap_time(**kw):
    """The emulated time at which case 0's capture is scheduled.

    Taken from the GENERATED Tcl, not from a re-derivation of the schedule: a
    reconstruction would have to redo the chunking and would agree with a bug
    in it (the reasoning `slots_out` is built on).
    """
    tcl = omsx_repl._tcl("/dev/null", CASES, BOOT, STEP,
                         kw.pop("cap_gap"), (), **kw)
    m = [float(t) for t in re.findall(
        r"after time ([0-9.]+) \{ puts \$__f \"case\.0=", tcl)]
    assert len(m) == 1, f"expected one scheduled capture, found {m}"
    return m[0]


print("R1  cap_gap DOES NOT MOVE THE CAPTURE")
base = cap_time(cap_gap=2.5)
check("a 2.5 s cap_gap and a 70 s cap_gap schedule the SAME capture",
      cap_time(cap_gap=70.0), base)
check("...and so does a 1000 s one", cap_time(cap_gap=1000.0), base)

print("R2  the budget a case actually gets is `step`")
# Two typed lines, so RUN is injected at BOOT + 1*STEP and the capture one
# STEP later. Spelled as the arithmetic rather than a literal so a change to
# the injection schedule fails this row instead of silently redefining it.
check("capture = RUN + step", round(base - (BOOT + STEP), 6), STEP)

print("R3  run_gap IS the knob, and it only ever pushes the capture LATER")
check("run_gap=60 moves the capture to RUN + 60",
      round(cap_time(cap_gap=2.5, run_gap=60.0) - (BOOT + STEP), 6), 60.0)
check("run_gap raises the capture above the cap_gap-only schedule",
      cap_time(cap_gap=2.5, run_gap=60.0) > base, True)
# A case may end in an explicit @WAIT that advances the clock on purpose; the
# driver takes max(t, t_run + run_gap) so such a wait is never discarded. A
# run_gap SHORTER than the natural schedule must therefore change nothing.
check("a run_gap shorter than `step` never pulls the capture EARLIER",
      cap_time(cap_gap=2.5, run_gap=0.5), base)

print("R4  KNIFE: this file can SEE a capture that moved")
# Without this row every check above would pass just as happily against a
# regex that matched nothing and a `cap_time` that returned a constant.
check("cap_time is sensitive to the schedule at all (run_gap=90 differs)",
      cap_time(cap_gap=2.5, run_gap=90.0) != base, True)
check("...and reports the value the knob asked for, not a fixed one",
      round(cap_time(cap_gap=2.5, run_gap=90.0)
            - cap_time(cap_gap=2.5, run_gap=60.0), 6), 30.0)

print()
if fails:
    print(f"{len(fails)} FAILED:")
    for f in fails:
        print(f"  {f}")
    sys.exit(1)
print("test_capture_budget: all rows passed")
