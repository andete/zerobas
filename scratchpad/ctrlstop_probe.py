#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWSTOP: is a HELD Ctrl-STOP delivered through `run_cases(holds=...)`, and
does `ON STOP GOSUB` see it?

Ctrl-STOP is TWO keys on DIFFERENT MATRIX ROWS -- CTRL row 6 bit $02 and STOP
row 7 bit $10 -- so it could not be expressed until `holds` learned to take a
SEQUENCE of (row, mask) pairs. This probe is that extension's CONTROL, and it
runs before any kwsweep row depends on it.

  c1_break   THE CONTROL. No trap at all: a program that spins for 300 FRAMES
             and then prints. If the combo is delivered the program BREAKS and
             `<NOBREAK>` never appears; if it is not, `<NOBREAK>` prints and
             nothing measured with this rig may be believed.
  c0_armed   `ON STOP GOSUB` + `STOP ON`: the handler must run instead.
  c2_noton   armed but NOT enabled -- arm != enable, so it must break like c1.

Frames, never iterations: the two machines differ 2.5-3.8x in interpreter speed
and a counted loop measures the interpreter.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CTRL_STOP = ((6, 0x02), (7, 0x10))      # modifier FIRST: down in order, up reversed

# 🔴 PRESSED AFTER THE `RUN`, NOT BEFORE IT. The default press is one STEP EARLY,
# which is right for a key the program SAMPLES -- but the REFERENCE's ROM flushes
# the type-ahead buffer while Ctrl-STOP is down, so that early press ate every
# injected line and the VG-8020 came back with a COMPLETELY BLANK SCREEN: no
# program, no `RUN`, nothing. zerobas does not flush, so ITS side of the same run
# typed and ran normally -- an apparatus asymmetry that reads exactly like a
# divergence, and it was found by DUMPING THE RAW CAPTURE rather than reasoning
# about the missing anchor.
# 🔴 AND IT MUST BE A SHORT PRESS, NOT A HOLD. Measured on the VG-8020: a 2 s
# Ctrl-STOP reads a clean `Break in 20`; a 5 s one leaves the screen COMPLETELY
# BLANK, and the 12 s default did the same. That is the reference's own behaviour
# at command level, not an injection fault -- CTRL alone and STOP alone both leave
# the program running to completion, so it is the COMBO and it is the DURATION.
# The stop-trap arc's own docstring says the same from the other side: the happy
# path appears with a brief TAP during a delay, not a hold.
# ⚠️ `hold_lead` is relative to the slot AFTER the `RUN` injection, so a
# positive value presses RUN+step+lead -- with a 0.5 lead that is RUN+3.0 s and a
# 2 s poll loop has already finished. The DEFAULT (None) presses at RUN+0.3,
# which is what a short press wants; only the DURATION had to change.
HOLD_LEAD = 0.5
HOLD_SECS = 2.0

CASES = [
    ("c1_break", ['T=TIME', 'IF TIME-T<200 THEN 20', 'PRINT"<NOBREAK>"']),
    ("c0_armed", ['C=0:ON STOP GOSUB 70:STOP ON', 'T=TIME',
                  'IF C=0 AND TIME-T<200 THEN 30', 'STOP OFF',
                  'PRINT"<";C;">"', 'END', 'C=C+1:RETURN']),
    ("c2_noton", ['C=0:ON STOP GOSUB 70', 'T=TIME',
                  'IF C=0 AND TIME-T<200 THEN 30', 'STOP OFF',
                  'PRINT"<";C;">"', 'END', 'C=C+1:RETURN']),
    # c3 keeps the trap ARMED AND ON across the readout -- c0's `STOP OFF` is what
    # zerobas breaks after. c4 is the bare form, which the reference ACCEPTS and
    # which CLEARS the handler slot (spec-traps-t4-sprite.md §1.5 says T1 shipped
    # ERR 2 here and that the fix was in T4's scope -- this is the re-verification).
    ("c3_armed2", ['C=0:ON STOP GOSUB 60:STOP ON', 'T=TIME',
                   'IF C=0 AND TIME-T<200 THEN 30',
                   'PRINT"<";C>0;">"', 'END', 'C=C+1:RETURN']),
    ("c4_bare",   ['C=0:ON STOP GOSUB 60:ON STOP GOSUB:STOP ON', 'T=TIME',
                   'IF C=0 AND TIME-T<200 THEN 30',
                   'PRINT"<";C;">"', 'END', 'C=C+1:RETURN']),
]


def main() -> int:
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
        print("===", mach)
        specs = [("stored", lines) for _, lines in CASES]
        raws = omsx_repl.run_cases(mach, specs, batch=False,
                                   holds=[CTRL_STOP] * len(CASES),
                                   hold_lead=HOLD_LEAD, hold_secs=HOLD_SECS)
        for (name, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            i = txt.rfind("RUN")
            print(f"  {name:10} {(txt[i:] if i >= 0 else txt)[:100]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
