#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-EMPTYOP — is the reference's bare-form `ERR 5` about an ABSENT operand or an EMPTY one?

D-BAREFORM measured seven bare-form divergences and split them by the face the
reference wants:

    KILL NAME FIELD LSET RSET   ->  ERR 5  Illegal function call
    COLOR KEY                   ->  ERR 24 Missing operand

\U0001f534 THAT SPLIT IS THE WHOLE QUESTION, AND FIXING BEFORE ANSWERING IT WOULD
BUILD THE WRONG THING. "Missing operand" is what a verb says when nothing is
there; `Illegal function call` is what one says about a value it does not like. If
the reference reaches ERR 5 by EVALUATING a bare `KILL` to the empty string and
rejecting THAT, the fix is about empty operands and a "no operand" test would be
wrong -- it would answer `KILL ""` differently from the reference.

The discriminator is an operand that is unmistakably PRESENT and empty:

  k.bare    KILL                 D-BAREFORM's row, re-taken as this probe's anchor
  k.empty   KILL ""              present, empty. Same as k.bare => the cause is
                                 EMPTINESS; different => the cause is ABSENCE
  k.name    KILL "A:NOSUCH.BAS"  CONTROL: a real name reaches the disk (ERR 53)
  l.bare    LSET                 the LSET/RSET half of the same split
  l.eq      LSET A$="x"          CONTROL: the legal form must NOT error
  l.noeq    LSET A$              present target, absent `=` -- absence again, one
                                 level in
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SRC = os.path.join(ROOT, "disk", "test720.dsk")
SIDES = {
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=10.0, reset=("NEW",)),
}
CASES = [
    ("k.bare",  'KILL',                 "anchor: D-BAREFORM says ERR 5 on the reference"),
    ("k.empty", 'KILL ""',              "PRESENT and empty -- same as k.bare => emptiness; different => absence"),
    ("k.name",  'KILL "A:NOSUCH.BAS"',  "CONTROL: a real name reaches the disk -> ERR 53"),
    ("l.bare",  'LSET',                 "the LSET/RSET half of the split"),
    ("l.eq",    'LSET A$="x"',          "CONTROL: the legal form must NOT error"),
    ("l.noeq",  'LSET A$',              "target present, `=` absent -- absence one level in"),
]


def main() -> int:
    out = {}
    for tag, stmt, note in CASES:
        row = {}
        for side, c in SIDES.items():
            dsk = os.path.join(tempfile.gettempdir(), f"zb_eop_{tag}_{side}.dsk")
            shutil.copy(SRC, dsk)
            p = ['10 ON ERROR GOTO 900', f'20 {stmt}',
                 '30 PRINT"ZQ";0;"QZ":END', '900 PRINT"ZQ";ERR;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", ["NEW"] + p + ["RUN"])], batch=False,
                reset=c["reset"], boot=c["boot"], step=4.0, run_gap=15.0,
                cap_gap=4.0, timeout=420.0, diska=dsk)[0] or "")
            v = [g for g in re.findall(r"ZQ\s*([0-9]+)\s*QZ", raw)
                 if not any(ch in g for ch in '"$;')]
            row[side] = int(v[-1]) if v else None
        out[tag] = row
        f = {s: ("<none>" if row[s] is None else
                 ("no error" if row[s] == 0 else f"ERR {row[s]}")) for s in SIDES}
        mark = "" if f["cf3300"] == f["zb"] else "   \U0001f534 DIFF"
        print(f"  {tag:8s} {stmt:20s} cf={f['cf3300']:9s} zb={f['zb']:9s}{mark}",
              flush=True)

    if out.get("l.eq", {}).get("cf3300") != 0:
        print(f"\n\U0001f534 THE l.eq CONTROL ERRORED ON THE REFERENCE "
              f"({out.get('l.eq')}) -- the legal form is not legal here, so the "
              f"instrument is wrong and no row means anything.")
        return 2
    kb, ke = out.get("k.bare", {}).get("cf3300"), out.get("k.empty", {}).get("cf3300")
    print(f"\n\U0001f3af THE ANSWER: k.bare={kb}  k.empty={ke}")
    if kb == ke:
        print("   SAME -> the reference's ERR 5 is about an EMPTY operand, not an "
              "absent one.\n   A 'no operand' test would answer `KILL \"\"` "
              "differently from the reference\n   and would be the wrong fix.")
    else:
        print("   DIFFERENT -> the ERR 5 really is the ABSENT-operand face, and a "
              "bare-form\n   test is the right shape.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
