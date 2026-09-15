#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KEYRIG: can `KEY n,"<str>"`'s ASSIGN form be read by HOLDING the key?

`KEY` is 1/4 forms. The existing `keykw` row already performs an assignment, but
it declares `FORM:list` and reads it back through `KEY LIST` -- a row declares ONE
form, so `assign` is uncovered. A function-key MACRO types its string into the
keyboard buffer when the key is pressed, and this tree already has a key-matrix
hold rig (`NEEDS-HOLD:6,0x20` is F1, proven by the `onkey` rows), so the assign
form can be read as the BEHAVIOUR it actually is rather than as a listing.

🔴 THE CONTROL IS THE DEFAULT MACRO, AND IT CAN FAIL. F1 defaults to
`color ` on an MSX, so holding F1 WITHOUT assigning must read `co` -- if it reads
`ZQ`, or nothing, the rig is not reaching the key and no row below it means
anything. c1 assigns `ZQ` and must read `ZQ`: the DIFFERENCE between the two cells
is the assignment, and neither cell is a constant.

⚠️ THE MACRO AUTO-REPEATS WHILE THE KEY IS HELD, which is what made the
`onkey` rows read `?noecho` on the faster reference -- the flood scrolled the
marker off. So c1 DISARMS (`KEY 1,""`) before it prints, and both cases take only
`LEFT$(A$,2)`.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK")
F1 = (6, 0x20)

# one element per line: `("stored", lines)` numbers them 10, 20, 30, ...
# 🔴 THE CONTROL DISARMS TOO, AND ITS FIRST CUT DID NOT. Without the
# `KEY 1,""` the default `color ` macro auto-repeated for the whole hold and
# filled the screen -- the cell came back as an unparseable flood. It still
# PROVED the rig reaches F1, but an unreadable cell is not a verdict, so the
# control now reads its two characters and shuts the macro off exactly as c1
# does. The disarm happens AFTER the read, so what it read is still the default.
CTRL = ['A$=""',
        "T=TIME",
        "A$=A$+INKEY$",
        "IF LEN(A$)<2 AND TIME-T<99 THEN 30",
        'KEY 1,"":PRINT"<";LEFT$(A$,2);">"',
        "END"]
ASSIGN = ['KEY 1,"ZQ":A$=""',
          "T=TIME",
          "A$=A$+INKEY$",
          "IF LEN(A$)<2 AND TIME-T<99 THEN 30",
          'KEY 1,"":PRINT"<";LEFT$(A$,2);">"',
          "END"]
CASES = [("c0_default", CTRL), ("c1_assign", ASSIGN)]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        raws = omsx_repl.run_cases(mach, [("stored", l) for _, l in CASES],
                                   batch=False, cap_gap=8.0,
                                   # 🔴 `holds` IS INDEXED PER CASE (`holds[i]`),
                                   # not applied globally -- one entry per case,
                                   # each a SEQUENCE of (row, mask) pairs.
                                   holds=[[F1] for _ in CASES], hold_secs=12.0)
        for (name, _), raw in zip(CASES, raws):
            t = " ".join("".join(raw or "").split())
            r = t.rfind("RUN")                   # the fence is in the LISTING too
            tail = t[r + 3:] if r >= 0 else t
            i = tail.find("<")
            j = tail.find(">", i + 1) if i >= 0 else -1
            print(f"  {name:11} {(tail[i:j+1] if i >= 0 and j > i else '?' + tail[:50])!r}",
                  flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
