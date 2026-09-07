#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DSKIFORM — is `DSKI$` a FUNCTION or a STATEMENT? The question the other three probes assumed away.

D-DSKI, D-DSKIWHERE and D-DSKIBYTES all drove `A$=DSKI$(0,0)` — the FUNCTION form —
and between them measured: the value is the empty string, the drive is validated
(ERR 62) but the SECTOR NUMBER IS NOT (sector 9999 on a 720 KB disk raises
nothing), and no page of $C000..$FFFF holds the sector afterwards; the only thing
that moves is a ~32-byte work-area record at $EB95..$EBB4.

🎯 EVERY ONE OF THOSE IS WHAT "THE READ NEVER HAPPENED" LOOKS LIKE. And there is a
reason to suspect the form rather than the verb: `basic_probe_kwsweep.py` writes
its `dsko` crunch body as **`dsko$0,0`** — a STATEMENT, no parens, no assignment —
while writing `dski` as `a$=dski$(0,0)`. That asymmetry was never examined; I
inherited the function form from it and built three probes on top.

⚠️ THIS PROBE ASKS ONLY WHICH FORMS PARSE AND RUN. It does not measure what they
do — that is the next probe's job, and doing both here would repeat the mistake of
reading a mechanism off a single face.

  f.func     A$=DSKI$(0,0)     the form all three earlier probes used
  f.stmt     DSKI$0,0          the statement form, as kwsweep writes DSKO$
  f.stmtsp   DSKI$ 0,0         the same with a space
  f.bare     DSKI$(0,0)        the function form used as a statement
  f.ctl      (no DSKI$ at all)  CONTROL -- must read 7

A row reads 7 if it ran clean, or the NEGATED error code if it trapped. A Syntax
error is ERR 2, so `-2` means "this form does not exist".
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

DSK = os.path.join(ROOT, "disk", "test720.dsk")
CF = "National_CF-3300"


def prog(body):
    return ['10 ON ERROR GOTO 900',
            f'20 {body}' if body else '20 REM no DSKI$ at all',
            '30 PRINT"ZQ";7;"QZ":END',
            '900 PRINT"ZQ";-ERR;"QZ":END']


CASES = [
    ("f.ctl",    prog(""),               "CONTROL: no DSKI$ -- must read 7"),
    ("f.func",   prog("A$=DSKI$(0,0)"),  "the form the three earlier probes used"),
    ("f.stmt",   prog("DSKI$0,0"),       "statement form, as kwsweep writes DSKO$"),
    ("f.stmtsp", prog("DSKI$ 0,0"),      "statement form with a space"),
    ("f.bare",   prog("DSKI$(0,0)"),     "function form used as a statement"),
]


def value(scr):
    if scr is None:
        return None
    for g in reversed(re.findall(r"ZQ\s*(-?\s*[0-9]+)\s*QZ", scr)):
        if any(ch in g for ch in '"$;'):
            continue
        try:
            return int(g.replace(" ", ""))
        except ValueError:
            continue
    return None


def main() -> int:
    out = {}
    for label, p, note in CASES:
        raw = "".join(omsx_repl.run_cases(
            CF, [("direct", ["NEW"] + p + ["RUN"])], batch=False,
            reset=("", "SCREEN 0", "NEW"), boot=14.0, step=5.0,
            run_gap=20.0, cap_gap=5.0, timeout=600.0, diska=DSK)[0] or "")
        out[label] = value(raw)
        v = out[label]
        face = "<none>" if v is None else ("ran clean" if v == 7 else f"ERR {-v}")
        print(f"  {label:9s} {face:14s} {note}", flush=True)

    if out.get("f.ctl") != 7:
        print(f"\n\U0001f534 THE CONTROL DID NOT READ 7 ({out.get('f.ctl')}) -- the "
              f"readout is broken and no row above is a reading.")
        return 2
    ran = [k for k, v in out.items() if k != "f.ctl" and v == 7]
    syn = [k for k, v in out.items() if v == -2]
    print(f"\n\U0001f3af FORMS THAT RUN CLEAN: {ran or 'NONE'}")
    print(f"   FORMS THAT ARE A SYNTAX ERROR (ERR 2): {syn or 'NONE'}")
    print("   Which form does the READ is NOT answered here -- running clean and "
          "doing\n   the work are different questions, and that is the next probe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
