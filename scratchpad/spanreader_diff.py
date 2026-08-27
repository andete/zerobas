#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Do the scratch probes' hand-rolled `[...]` readers actually MISREAD?

The filed item says eleven sweep probes re-implement `omsx_repl`'s reader and
that this is the trap the reader exists for. The cheap response is to rewrite
them; that would be wrong twice over -- these are ONE-SHOT instruments whose
recorded output is the sweep's evidence, so changing the code changes what the
record is reproducible from. The question worth answering first is whether the
copies actually differ ON THE CASE THAT MATTERS.

`omsx_repl.result_span_after_echo` exists so *"an aborted case's echoed `[` is
not misread as printed output"*. So: build screens where an echoed command
CONTAINS a bracket, and compare.

⚠️ THE TRAP SCREEN IS THE INSTRUMENT'S OWN CONTROL. A pair of readers that
agree on ordinary screens tells you nothing; they must be shown to DISAGREE
somewhere, or this script cannot detect a difference at all.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

COLS, ROWS = omsx_repl.COLS, omsx_repl.ROWS


def screen(*rows):
    s = "".join(r.ljust(COLS)[:COLS] for r in rows)
    return s.ljust(COLS * ROWS)[:COLS * ROWS]


def handrolled(scr):
    """The shape all eight copies share: every [...] on the flattened screen."""
    flat = " ".join(scr[r * COLS:(r + 1) * COLS].rstrip() for r in range(ROWS))
    out, i = [], 0
    while (a := flat.find("[", i)) >= 0 and (b := flat.find("]", a)) >= 0:
        out.append(flat[a + 1:b].strip()); i = b + 1
    return out


CASES = [
    ("plain",
     screen("Ok", 'PRINT"[";1+1;"]"', "[ 2 ]", "Ok"),
     "an ordinary value row -- both readers must agree"),
    ("echo-carries-bracket",
     screen("Ok", '10 PRINT"[";ERR;"]"', "RUN", "[ 13 ]", "Ok"),
     "🎯 THE TRAP: the stored line's echo contains the marker literally"),
    ("aborted",
     screen("Ok", 'A%="X":PRINT"[";1;"]"', "Type mismatch", "Ok"),
     "🎯 the case the shared reader was written for: NO output, echo only"),
    ("two-values",
     screen("Ok", "RUN", "[ 1 ]", "[ 2 ]", "Ok"),
     "two real spans after one echo"),
]

print(f"{'case':22s} {'hand-rolled':28s} {'result_span_after_echo':24s}")
disagree = 0
for name, scr, why in CASES:
    hr = handrolled(scr)
    cmd = "RUN" if "RUN" in scr else 'PRINT"[";1+1;"]"'
    sh = omsx_repl.result_span_after_echo(scr, cmd)
    same = (sh in hr) if (hr and sh is not None) else (not hr and sh is None)
    if not same or (hr and sh is not None and hr[0] != sh):
        disagree += 1
        mark = "DIFF"
    else:
        mark = " ok "
    print(f"{name:22s} {str(hr):28s} {str(sh):24s} {mark}")
    print(f"    {why}")
if not disagree:
    print("\nINSTRUMENT FAULT (rc 2): the two readers agreed on EVERY case, "
          "including the trap ones. This script cannot detect a difference, so "
          "'they agree' is not a result.")
    sys.exit(2)
print(f"\n{disagree} of {len(CASES)} cases separate the two readers.")
