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

🔴🔴 STATUS 2026-09-14: **THIS PROBE DOES NOT YET MEASURE ANYTHING, AND IT SAYS SO
RATHER THAN BEING DELETED.** Its CONTROL case fails: `bounded2` -- the known-good
two-argument shape the sweep scores successfully every run -- reads empty here,
with `capture="screen"` and with the refcache forced off. So the capture shape is
still wrong, not PAINT. Three things are ruled out and recorded so the next
attempt does not repeat them:
  * NOT the echo anchor alone -- `capture="screen"` was added and changed nothing;
  * NOT the refcache -- `ZEROBAS_REFCACHE=0` was forced and changed nothing (the
    first run HAD been served 3 cached readings, which is its own lesson);
  * NOT slowness -- `cap_gap=25.0` and `timeout=420.0` are far beyond the sweep's.
⚠️ The next step is to read how `basic_probe_kwsweep` actually builds a NOECHO
capture (`marker_tail` + the `capture="screen"` contract) and MIRROR IT, rather
than assume `run_cases`' defaults resemble it. **A probe whose control fails
measures nothing, and saying so is the whole value of having had a control.**

The four cases, and what each separates:
  bounded2  the known-good TWO-argument shape inside a box -- the control. If this
            loses its marker too, the fault is the probe, not PAINT.
  bounded3  the SAME, with an explicit border. Differs from `bounded2` in exactly
            one argument, so a `?nomarker` here IS the 3-argument form.
  unbounded a 2-argument flood with NO box -- the whole screen. If THIS loses its
            marker, slowness alone is enough to do it and the sweep row's second
            reading proved nothing.
  leak      3-argument, border 7, nothing drawn in 7: the flood must PASS the box.
            The form the sweep row wanted, measured where timing cannot hide it.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "probes", "lib"))
import omsx_repl                                                    # noqa: E402

BOX = 'SCREEN2:LINE(10,10)-(20,20),15,B'
CASES = {
    "bounded2":  [f'10 {BOX}:PAINT(15,15),11',
                  '20 A=POINT(15,15):B=POINT(25,25)',
                  '30 SCREEN0:PRINT"[P";A;B;"]"', 'RUN'],
    "bounded3":  [f'10 {BOX}:PAINT(15,15),11,15',
                  '20 A=POINT(15,15):B=POINT(25,25)',
                  '30 SCREEN0:PRINT"[Q";A;B;"]"', 'RUN'],
    "unbounded": ['10 SCREEN2:PAINT(15,15),11',
                  '20 A=POINT(15,15):B=POINT(25,25)',
                  '30 SCREEN0:PRINT"[R";A;B;"]"', 'RUN'],
    "leak":      [f'10 {BOX}:PAINT(15,15),11,7',
                  '20 A=POINT(15,15):B=POINT(25,25)',
                  '30 SCREEN0:PRINT"[S";A;B;"]"', 'RUN'],
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
        print(f"  {key:10} {' '.join(str(caps[0]).split())[-76:]!r}", flush=True)
