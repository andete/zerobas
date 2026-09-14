#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWPAINT2 — does `PAINT(x,y),C,B` fault, or does the FLOOD outrun the capture?

🔴 AND THE FIRST CUT OF THIS PROBE FAILED ITS OWN CONTROL, WHICH IS WHY THE
CONTROL IS THERE. Every case read empty -- including `bounded2`, the known-good
TWO-argument shape the sweep measures successfully every run. The cause was the
probe: `run_cases` anchors its default capture on the ECHOED COMMAND, and
`SCREEN 2` ... `SCREEN 0` ERASES THE ECHO. That is exactly what `NOECHO:` exists
for in the sweep, and this probe had no equivalent until `capture="screen"` was
passed. THE APPARATUS IS PART OF THE MEASUREMENT, again.

🔴 THE SWEEP ROW COULD NOT TELL THESE APART, AND THREE ATTEMPTS IS WHERE GUESSING
STOPS. `PAINT(15,15),11,15` inside a drawn box read `?nomarker` on BOTH machines.
Reduced to `SCREEN2:PAINT(15,15),11,15` with no box it read `?nomarker` again --
but with nothing to stop it that floods the WHOLE screen, which is slow, so the
second reading cannot separate the two causes. Every case below is its OWN boot
with a long capture gap, so slowness cannot masquerade as a fault.

🎚️ THE BAR STAYS AT N=3 WHATEVER THIS SAYS. docs/spec-basic-graphics-g5.md is
explicit that the border is supported here -- the FOURTH argument is the ERR 2,
and the border `B` is parsed and RANGE-CHECKED (ERR 5 outside 0..255) -- so a
missing reading is a missing ROW, not a missing form.

🔴🔴 ITS CONTROL FAILED FIRST, AND THE CAUSE WAS THE *REPORTING*, NOT THE CAPTURE.
`bounded2` -- the known-good two-argument shape the sweep scores every run -- read
EMPTY, and so did everything else. Three causes were ruled out (not the echo
anchor: `capture="screen"` changed nothing; not the refcache: `ZEROBAS_REFCACHE=0`
changed nothing, though the first run HAD been served 3 cached readings; not
slowness: `cap_gap=25.0`, `timeout=420.0`). ✅ THE FAULT WAS `raw[-76:]` -- I was
slicing the BOTTOM of a 24x40 screen dump, and **`SCREEN 0` HOMES THE CURSOR**, so
these cases print at the TOP and the tail holds nothing but the function-key line.
`clearhimem_probe.py` gets away with a tail slice only because its cases never
change SCREEN. The probe now FINDS ITS MARKER the way `marker_tail` does.
⚠️ **A probe whose control fails measures nothing** -- and without that control
this would have been reported as "PAINT's 3-argument form faults on both
machines".

📊 MEASURED 2026-09-14, and the answer is NEITHER of the two I set out to
separate. On BOTH machines:
  same15    `[P 15  4 ]`  -- fill colour EQUAL to the box colour completes at once
  fill11    (blank)       -- a DIFFERENT fill colour never reaches the PRINT
  border15  (blank)       -- nor does the 3-ARGUMENT form with a border EQUAL to
                             the box colour, which is the CORRECT usage
  trapped   (blank)       -- and an `ON ERROR GOTO` handler NEVER FIRES, so it is
                             NOT raising an error: it simply has not finished
                             30 seconds of capture gap later
🎯 SO THE SWEEP'S `paintkw` ROW PASSES ONLY BECAUSE ITS FILL COLOUR EQUALS THE
BOX COLOUR -- the fill stops on its first cell. Every row with a different fill
colour, WITH OR WITHOUT an explicit border, outruns the capture. Whether that is
"the border is not honoured so it floods the screen" or "PAINT is simply this slow
in SCREEN 2" is the NEXT question and wants a much longer gap (try cap_gap=120)
or a far smaller filled region.
⚠️ WHAT THIS DOES **NOT** SAY: it does not say the 3-argument form is broken.
No error is raised, and docs/spec-basic-graphics-g5.md is explicit that the border
is parsed and RANGE-CHECKED here. PAINT stays at 1/3 for want of a ROW, not a form.

"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "probes", "lib"))
import omsx_repl                                                    # noqa: E402

BOX = 'SCREEN2:LINE(10,10)-(20,20),15,B'
MARK = {"same15": "[P", "fill11": "[Q", "border15": "[R", "trapped": "[S"}
CASES = {
    # 🟢 THE CONTROL, AND IT PASSES: this is the sweep's own `paintkw` shape, fill
    #    colour EQUAL to the box colour. Reads `[P 15  4 ]`.
    "same15":   [f'10 {BOX}:PAINT(15,15),15',
                 '20 A=POINT(15,15):B=POINT(25,25)',
                 '30 SCREEN0:PRINT"[P";A;B;"]"', 'RUN'],
    # a DIFFERENT fill colour, border defaulting to it
    "fill11":   [f'10 {BOX}:PAINT(15,15),11',
                 '20 A=POINT(15,15):B=POINT(25,25)',
                 '30 SCREEN0:PRINT"[Q";A;B;"]"', 'RUN'],
    # the 3-argument form, border EQUAL to the box colour -- the correct usage
    "border15": [f'10 {BOX}:PAINT(15,15),11,15',
                 '20 A=POINT(15,15):B=POINT(25,25)',
                 '30 SCREEN0:PRINT"[R";A;B;"]"', 'RUN'],
    # the same, with an ON ERROR handler: does it FAULT, or just not finish?
    "trapped":  ['10 ON ERROR GOTO 50', f'20 {BOX}:PAINT(15,15),11,15',
                 '30 SCREEN0:PRINT"[S OK]"', '40 END',
                 '50 SCREEN0:PRINT"[S ERR";ERR;"]"', 'RUN'],
}

MACHINES = [("Philips_VG_8020", 8.0, ("NEW", "CLS")),
            ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0, ("NEW", "CLS"))]

for machine, boot, reset in MACHINES:
    print(f"=== {machine} ===", flush=True)
    for key, lines in CASES.items():
        caps = omsx_repl.run_cases(
            machine, [(key, list(reset) + lines)],
            batch=False, boot=boot, step=3.0, cap_gap=25.0, timeout=420.0,
            capture="screen")
        raw = str(caps[0] or "")
        # 🔴 FIND THE MARKER, DO NOT SLICE THE TAIL. The first cut printed
        # `raw[-76:]` -- the BOTTOM of a 24x40 screen dump -- and every case read
        # empty, CONTROL INCLUDED. `SCREEN 0` HOMES THE CURSOR, so these rows
        # print at the TOP and the tail holds nothing but the function-key line.
        # `clearhimem_probe.py` gets away with a tail slice because its cases
        # never change SCREEN and print where the cursor already was.
        mk = MARK[key]
        rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
                for r in range(omsx_repl.ROWS)]
        hit = next((t for t in reversed(rows) if mk in t), None)
        print(f"  {key:10} {hit if hit is not None else '?nomarker'!r}",
              flush=True)
