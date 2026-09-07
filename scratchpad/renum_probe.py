#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-RENUM — RENUM and DELETE have bodies but nothing runs them.

`make kwsweep` scores both `crunch-only — support UNKNOWN`, with stated reasons:
RENUM "needs a program to be visible", DELETE "would eat the batch's own
program". Both are true of a shared single-line batch and neither is true of a
dedicated probe. So "implemented" has been a claim about `ex_renum` / `ex_delete`
existing in basic/program.asm, not about the machine.

## The readout is (ERR, ERL), not a listing

Comparing LIST output across machines is a text-diff over a 40-column screen
with three different prompts. `ERL` is the LINE NUMBER an error occurred on, so
one fence carries both what happened and where:

    1 ON ERROR GOTO 100
    10 X=1
    20 ERROR 7
    30 ERROR 5
    100 PRINT"ZQ";ERR;",";ERL;"QZ":END

Un-renumbered that reads `7,20`. After a bare `RENUM` the lines become
10/20/30/40/50, so the ERROR 7 moves to line 30 and it reads `7,30`. The number
IS the renumbering.

🎯 AND THE HANDLER IS PART OF THE TEST. `ON ERROR GOTO 100` is a LINE REFERENCE:
RENUM has to rewrite it or the trap stops resolving. Reference rewriting is the
half of RENUM that is easy to get wrong and invisible to a listing that only
checks the left margin, so every row here exercises it by construction — if the
reference were not rewritten the row would read `<NO READING>` or an Undefined
line number, not a wrong-but-plausible number.

`r.goto` adds a FORWARD reference in the body for the same reason, and `r.step`
uses `RENUM 100,,5` so the start and the step are read separately: a single
row cannot tell "starts at the right place" from "steps by the right amount".

⚠️ AUTO IS NOT HERE, and the reason is the verb: it enters auto-line-number mode
and swallows every following line as program text. Driving it needs an escape and
a REPL that can prove it left the mode; that is a different probe and is named
here rather than quietly skipped.
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

PROG = ['1 ON ERROR GOTO 100',
        '10 X=1',
        '20 ERROR 7',
        '30 ERROR 5',
        '100 PRINT"ZQ";ERR;",";ERL;"QZ":END']

# a forward GOTO whose target must be rewritten too
PROGG = ['1 ON ERROR GOTO 100',
         '10 GOTO 30',
         '20 ERROR 7',
         '30 ERROR 5',
         '100 PRINT"ZQ";ERR;",";ERL;"QZ":END']

CASES = [
    ("c.base",   PROG,  None,            "CONTROL: no command -- 7 at line 20"),
    ("r.plain",  PROG,  "RENUM",         "bare RENUM: 10/20/30/40/50, so 7 at 30"),
    ("r.start",  PROG,  "RENUM 100",     "new start, default step 10 -> 7 at 120"),
    ("r.step",   PROG,  "RENUM 100,,5",  "start AND step, read separately -> 7 at 110"),
    ("r.goto",   PROGG, "RENUM",         "a forward GOTO must be rewritten too"),
    ("d.one",    PROG,  "DELETE 20",     "the ERROR 7 line goes -> 5 at 30"),
    ("d.range",  PROG,  "DELETE 20-30",  "both error lines go -> no error at all"),
    ("d.from",   PROG,  "DELETE -20",    "everything up to 20 -- takes the handler"),
]


def run(side, prog, cmd):
    machine, boot, reset = SIDES[side]
    # 🔴 A DIRECT-MODE READ AFTER `RUN`, because `<no fence>` is not an
    # outcome. `d.from` deletes the handler along with everything up to line 20,
    # so its error goes UNTRAPPED and the program prints nothing -- which is
    # indistinguishable from a wedged machine or a lost capture
    # [[an-unnamed-outcome-reads-as-no-outcome]]. ERR/ERL survive into direct
    # mode, so asking for them there turns that row into a READING.
    lines = (list(reset) + prog + ([cmd] if cmd else []) + ["RUN"]
             + ['PRINT"ZR";ERR;",";ERL;"RZ"'])
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", lines)], batch=False, reset=(),
        boot=boot, step=5.0, cap_gap=12.0, timeout=300.0)[0] or "")
    m = re.search(r"ZQ\s*(-?\d+)\s*,\s*(-?\d+)\s*QZ", raw)
    if m:
        return f"{int(m.group(1))},{int(m.group(2))}"
    d = re.search(r"ZR\s*(-?\d+)\s*,\s*(-?\d+)\s*RZ", raw)
    if d:
        # the handler never ran; this is the UNTRAPPED state, read directly
        return f"u{int(d.group(1))},{int(d.group(2))}"
    return "<NO READING>"


def main() -> int:
    rows = []
    for tag, prog, cmd, note in CASES:
        got = {s: run(s, prog, cmd) for s in SIDES}
        rows.append((tag, cmd, note, got))
        print(f"  {tag:9s} {str(cmd):14s} "
              + "  ".join(f"{s}={got[s]:>11s}" for s in SIDES), flush=True)

    print(f"\n{'row':9s} {'command':15s} {'vg8020':>11s} {'cf3300':>11s} "
          f"{'zb':>11s}   verdict")
    dis, split = [], []
    for tag, cmd, note, g in rows:
        v, c, z = g["vg8020"], g["cf3300"], g["zb"]
        if v != c:
            verdict = "REFS SPLIT"; split.append(tag)
        elif z != v:
            verdict = "🔴 DIFF"; dis.append(tag)
        else:
            verdict = "SAME"
        print(f"{tag:9s} {str(cmd):15s} {v:>11s} {c:>11s} {z:>11s}   {verdict}")
        print(f"          {note}")
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'}"
          + (f"; REFS-SPLIT: {split}" if split else "") + " ===")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
