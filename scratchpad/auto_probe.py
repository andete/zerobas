#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-AUTO — the last of RENUM / DELETE / AUTO, and the one kwsweep cannot run.

D-RENUM measured RENUM and DELETE (8 rows, three machines, no divergence) and
left AUTO named rather than skipped: *"it enters auto-line-number mode and
swallows every following line as program text. Driving it needs an escape and a
REPL that can prove it left the mode."* `make kwsweep` lists it crunch-only for
the same reason -- "INTERACTIVE: enters auto-line-number mode and swallows all
following input".

## The escape is the whole problem, so it is a MEASURED variable here

Lines typed after `AUTO` are consumed as PROGRAM TEXT at the numbers AUTO
assigns. Nothing after them runs until the mode is left, so the probe has to
break out. Ctrl-C ($03) is injected straight into KEYBUF, the same path every
other line takes -- if it is the wrong key the row reads `<NO READING>` rather
than a wrong answer, because `RUN` would have been swallowed too.

## The readout is (ERR, ERL), as in D-RENUM

The handler is typed BEFORE `AUTO`, at numbers AUTO will not reach:

    1   ON ERROR GOTO 100        typed normally
    100 PRINT ... ERR, ERL       typed normally
    AUTO 200,5
    X=1                          -> AUTO assigns 200
    ERROR 7                      -> AUTO assigns 205
    <escape>
    RUN                          -> traps at whatever number AUTO gave line 2

So `7,205` says AUTO started at 200 and stepped by 5. `a.plain` uses a bare
`AUTO`, whose documented default is 10,10 -- so `7,20`.

⚠️ `a.esc` IS A CONTROL ON THE INSTRUMENT, NOT ON THE MACHINE: it types the same
program with NO `AUTO` and explicit numbers. If it fails, the escape or the
readout is broken and the AUTO rows say nothing about AUTO.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (os.environ.get("ZEROBAS_BASIC_MACHINE",
                          "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
}

# 🔴 THE HANDLER MUST OUTNUMBER EVERY LINE AUTO WILL GENERATE. The first
# cut put it at 100: `AUTO 200,5` then makes 200/205, so RUN reached the HANDLER
# first and printed `0,0` -- ERR 0 at ERL 0, a perfectly plausible-looking pair
# from a program that never ran its body. Bare AUTO starts at 10, so a.plain
# worked and a.start did not, which is what made it look like an AUTO difference
# rather than my line numbering. 9000 is above both.
HEAD = ['1 ON ERROR GOTO 9000',
        '9000 PRINT"ZA";ERR;",";ERL;"AZ":END']
ESC = "\x03"

CASES = [
    ("a.esc",    HEAD + ['200 X=1', '205 ERROR 7'],
     "CONTROL: no AUTO at all, numbers typed -- must read 7,205"),
    ("a.start",  HEAD + ['AUTO 200,5', 'X=1', 'ERROR 7', ESC],
     "AUTO 200,5 -- start AND step, so 7,205"),
    ("a.plain",  HEAD + ['AUTO', 'X=1', 'ERROR 7', ESC],
     "bare AUTO -- documented default 10,10, so 7,20"),
    # 🎯 THE ESCAPE'S OWN CONTROL. Without it, "the references exit on $03"
    # rests on the $03 line being the CAUSE rather than on AUTO ending some other
    # way. This row is a.start with the ESC REMOVED: if the references still read
    # 7,205 the escape is not what ends the session and the whole finding is
    # misattributed [[a-mechanism-inferred-from-one-observation]].
    ("a.noesc",  HEAD + ['AUTO 200,5', 'X=1', 'ERROR 7'],
     "CONTROL on the ESCAPE: same as a.start with NO Ctrl-C -- RUN should be "
     "swallowed on every machine"),
]


def run(side, prog):
    machine, boot, reset = SIDES[side]
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + prog + ["RUN"])], batch=False,
        reset=(), boot=boot, step=6.0, cap_gap=25.0, timeout=300.0)[0] or "")
    # the fence is in the source the machine echoes: LAST match, and refuse any
    # match still carrying source punctuation [[trapsvc-echo-fence]]
    for g in reversed(re.findall(r"ZA\s*([^,]*),\s*([^A]*)AZ", raw)):
        if any(ch in "".join(g) for ch in '"$;'):
            continue
        try:
            return f"{int(g[0])},{int(g[1])}"
        except ValueError:
            continue
    return "<NO READING>"


def main() -> int:
    rows = []
    for tag, prog, note in CASES:
        got = {s: run(s, prog) for s in SIDES}
        rows.append((tag, note, got))
        print(f"  {tag:8s} " + "  ".join(f"{s}={got[s]:>13s}" for s in SIDES),
              flush=True)

    print(f"\n{'row':8s} {'vg8020':>13s} {'cf3300':>13s} {'zb':>13s}   verdict")
    dis, split = [], []
    for tag, note, g in rows:
        v, c, z = g["vg8020"], g["cf3300"], g["zb"]
        if v != c:
            verdict = "REFS SPLIT"; split.append(tag)
        elif z != v:
            verdict = "🔴 DIFF"; dis.append(tag)
        else:
            verdict = "SAME"
        print(f"{tag:8s} {v:>13s} {c:>13s} {z:>13s}   {verdict}")
        print(f"         {note}")
    if rows[0][2]["zb"] != "7,205":
        print("\n🔴 THE CONTROL a.esc DID NOT READ 7,205 -- the readout or the "
              "typing is broken, so the AUTO rows below it say nothing about AUTO.")
        return 2
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'}"
          + (f"; REFS-SPLIT: {split}" if split else "") + " ===")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
