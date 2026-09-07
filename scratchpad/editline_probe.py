#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-EDITLINE — two of D-EDITSCOUT's named unknowns: the SECOND reference, and
where a logical line STARTS.

docs/spec-basic-editscout.md §6 lists what the placement scout did NOT price.
Two of its bullets are cheap and decisive, and this probe takes both:

  * *"`CF-3300` was not run. One reference only, so nothing here separates
    'MSX1 BASIC' from 'this VG-8020'."*  Every row below runs on BOTH.
  * *"How the reader knows where a logical line STARTS. The reference keeps
    per-row continuation bookkeeping; zerobas has none, and whether it can infer
    the boundary (a predecessor row filled to LINLEN) is unmeasured."*

## The boundary question, in the form that decides the implementation

A VRAM reader that walks BACK from the cursor has to stop somewhere. The cheapest
rule available to zerobas — which keeps no per-row state — is *"keep walking while
the row above is filled to the last column"*. This probe asks whether that rule
agrees with the reference, by building a full row that a NAIVE walker would
swallow and a bookkeeping one would not:

    PRINT STRING$(40,"'");"A=A+1:PRINT A"

One `PRINT`, 53 characters, so row 0 is EXACTLY full (40 apostrophes) and row 1
holds the payload. Cursor-up onto row 1, Enter.

🎯 THE READOUT IS THE APOSTROPHE, WHICH IS `REM` IN MSX BASIC. If the machine
re-enters ROW 1 ALONE the payload runs and the counter reads **2**. If it walks
back and takes rows 0+1 as ONE logical line, the line begins with `'` and the
whole thing is a COMMENT — the counter stays **1**. One row, two mechanisms,
opposite readings.

🔴 THE FIRST CUT OF THIS PROBE WAS BLIND, IN D-EDITSCOUT §3's OWN WAY, AND ITS
DOCSTRING CLAIMED OTHERWISE. It read the SCREEN, asserting that *"a re-entry that
was commented out still ECHOES the line and still prints `Ok`, and one that never
happened prints neither."* Both halves are wrong: the MSX editor does not re-echo
a line already on the screen, and a REM'd re-entry prints `Ok` **over the `Ok`
already there** — so `x.reenter` came back BYTE-IDENTICAL to `x.noup` on both
references, which is what "nothing happened" looks like too.

🎯 THE FIX IS TO READ THE VARIABLE, NOT THE SCREEN. A separate typed line after
the re-entry — `PRINT"ZQ";A;"QZ"` — lands on a FRESH row that no earlier output
can coincide with, and its value counts executions:

    A=0  the payload never ran   -> rows N+N+1 taken TOGETHER and REM'd
    A=1  the payload ran ONCE    -> row N+1 taken ALONE, boundary at the row start
    A=2  ... only reachable in `x.plain`, which executes it before re-entering

⚠️ AND THE WIDTH WAS AN ASSUMPTION, MEASURED WRONG. `STRING$(40,...)` was chosen
to fill a row exactly; the first run showed **35** apostrophes on the row for the
VG-8020 and **39** for the CF-3300, so the two references were not even running
the same construction and the payload row began with a stray `'` on one of them.
`WIDTH 40` is now set on every side, which makes the fill exact and the row
boundary the same on all three.

🎯 `x.plain` IS THE POSITIVE CONTROL AND EVERY OTHER ROW DEPENDS ON IT: the
payload typed with NO apostrophes, executed, then re-entered. It MUST read 2 on
both references (D-EDITSCOUT measured exactly this) and 1 on zerobas. If it does
not, the cursor-up count or the typing is wrong and the boundary rows say nothing.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW", "WIDTH 40")),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=2.5,
                   reset=("", "SCREEN 0", "NEW", "WIDTH 40")),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=8.0, step=2.5, reset=("NEW", "WIDTH 40")),
}
COLS, ROWS = 40, 24
UP = "\x1e"
PAY = "A=A+1:PRINT A"
# With WIDTH 40 the 40 apostrophes fill one row EXACTLY and the payload starts at
# the next row's column 0. `'` is REM, so a walker that includes the filled row
# comments the payload out.
FILL = 'PRINT STRING$(40,"\'");"' + PAY + '"'
ASK = 'PRINT"ZQ";A;"QZ"'

CASES = [
    ("x.plain", ['CLS', PAY, UP * 3, ASK],
     "POSITIVE CONTROL: no apostrophes, executed then re-entered. MUST read "
     "A=2 on both references (D-EDITSCOUT's own row) and A=1 on zerobas"),
    ("x.noup", ['CLS', FILL, ASK],
     "BASELINE: the two-row screen is built and NOTHING is re-entered. The "
     "payload is PRINTED text, never executed, so A=0 everywhere"),
    ("x.reenter", ['CLS', FILL, UP * 2, ASK],
     "cursor UP x2 onto the PAYLOAD row, Enter. A=1 => the row was taken ALONE "
     "(boundary at the row start); A=0 => the filled row above was taken too "
     "and the leading ' REM'd the line"),
    # 🔴 x.reenter ALONE CANNOT ANSWER THE QUESTION IT WAS WRITTEN FOR.
    # Its filled row was produced by a PRINT that WRAPPED, which sets BOTH
    # candidate causes at once: the row is full on screen AND CHPUT recorded a
    # wrap. "The row above is full" and "the BIOS marked a continuation" agree on
    # every row above [[two-rules-that-coincide-on-every-row-you-have]].
    # 🎯 x.vpoke SEPARATES THEM: the filling row is written straight into
    # the name table with VPOKE, so it is full on screen and CHPUT never ran.
    #   A=0  the walker took it   -> the rule is SCREEN-ONLY, and zerobas (which
    #                               keeps no per-row state) can match it as-is
    #   A=1  the walker stopped   -> the reference has BOOKKEEPING the screen does
    #                               not carry, and zerobas would need its own
    # Layout, read off the capture rather than predicted: `Ok` at r00, the LOCATE
    # line echoes at r01 and prints the payload at r05, the VPOKE line echoes at
    # r07 and fills r04 (4*40 = 160), and the cursor ends four rows below the
    # payload. The re-entry's own output then lands at r06 and its `Ok` at r07,
    # over the first two characters of the VPOKE echo -- which is what
    # `OkRI=0TO39:...` in the capture is, and it is the evidence that the Enter
    # landed on r05 and not on the apostrophe row above it.
    ("x.vpoke", ['CLS', 'LOCATE 0,5:PRINT"' + PAY + '"',
                 'FORI=0TO39:VPOKE160+I,39:NEXT', UP * 4, ASK],
     "SEPARATOR: the full row above the payload is written by VPOKE, so CHPUT "
     "never wrapped. A=0 => the rule is SCREEN-ONLY; A=1 => the reference keeps "
     "bookkeeping the screen does not carry"),
    ("x.abovefill", ['CLS', FILL, UP * 3, ASK],
     "cursor UP x3 onto the APOSTROPHE row itself. A=0 on any reading -- a "
     "line that BEGINS with ' is a REM however far forward the walker goes. "
     "Included to show the UP count spans the two rows it is meant to"),
]


def value(scr):
    """A from the ZQ...QZ fence. The fence text is also in the SOURCE the screen
    still shows, so take the LAST match and refuse any carrying source
    punctuation [[trapsvc-echo-fence]]."""
    if scr is None:
        return None
    for g in reversed(re.findall(r"ZQ\s*([^Q]*)QZ", scr)):
        if any(ch in g for ch in '"$;'):
            continue
        try:
            return int(g)
        except ValueError:
            continue
    return None


def rows(scr):
    if scr is None:
        return None
    return [(r, scr[r * COLS:(r + 1) * COLS].rstrip())
            for r in range(ROWS) if scr[r * COLS:(r + 1) * COLS].strip()]


def main():
    res = {}
    for s, c in SIDES.items():
        res[s] = omsx_repl.run_cases(
            c["machine"], [("direct", l) for _, l, _ in CASES], batch=True,
            reset=c["reset"], boot=c["boot"], step=c["step"],
            verify_delivery=False)
        print(f"  {s} captured", flush=True)

    print(f"\n{'row':14s} {'vg8020':>8s} {'cf3300':>8s} {'zb':>8s}   A = times the payload executed")
    vals = {}
    for i, (label, lines, asks) in enumerate(CASES):
        v = {s: value(res[s][i]) for s in SIDES}
        vals[label] = v
        cell = {s: ("<none>" if v[s] is None else str(v[s])) for s in SIDES}
        print(f"{label:14s} {cell['vg8020']:>8s} {cell['cf3300']:>8s} "
              f"{cell['zb']:>8s}")
        print(f"    {asks}")

    for i, (label, lines, asks) in enumerate(CASES):
        print(f"\n=== {label} screens")
        for side in SIDES:
            rr = rows(res[side][i])
            if rr is None:
                print(f"  {side:8s} <NO CAPTURE>")
                continue
            print(f"  {side:8s} " + " | ".join(f"r{r:02d}:{t}" for r, t in rr))

    p = vals.get("x.plain", {})
    if p.get("vg8020") != 2 or p.get("cf3300") != 2:
        print(f"\n\U0001f534 THE POSITIVE CONTROL DID NOT READ 2 ON BOTH "
              f"REFERENCES ({p}) -- the cursor-up count or the typing is wrong, "
              f"and NO boundary row below says anything.")
        return 2
    r, v = vals.get("x.reenter", {}), vals.get("x.vpoke", {})
    print("\n\U0001f3af THE BOUNDARY READING is the PAIR, not either row alone:")
    print(f"     x.reenter (PRINT-wrapped fill) {r}")
    print(f"     x.vpoke   (VPOKE fill, no CHPUT) {v}")
    if r.get("vg8020") == 0 and v.get("vg8020") == 0:
        print("  => both walked: the reference's rule is satisfied by the SCREEN "
              "alone, so a zerobas VRAM reader needs no per-row bookkeeping.")
    elif r.get("vg8020") == 0 and v.get("vg8020") == 1:
        print("  => the PRINT wrap was walked and the VPOKE fill was NOT: the "
              "reference keeps CONTINUATION STATE the screen does not carry, and "
              "zerobas would have to keep its own. That is a real cost the "
              "placement scout did not price.")
    else:
        print("  => neither pattern; read the screens before concluding anything.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
