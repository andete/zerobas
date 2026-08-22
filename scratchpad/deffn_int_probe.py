#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DEFFN: which half of the INT result path is answering -3392?

Six rows of `make deffn-acceptance` -- and only six -- read the SAME constant
`-3392` ($F2C0) on the scaffolded build, and every one of them has FN_RTYPE = 2
(either `DEFINT A-Z` or an explicit `%` on the FUNCTION name). Every other body
shape agrees. A CONSTANT that does not depend on the body says the reading is
not the body's value at all, so this splits the path:

  i.const   the body is a literal            -> is the coercion itself broken?
  i.noco    the FN's type is DOUBLE          -> the same body without coercion
  i.dblres  `%` formal, double function      -> coercion the other way
  i.varptr  VARPTR of the formal, DEFINT     -> is the SLOT where we think?
  i.peek    PEEK of the slot's own bytes     -> what is actually stored there
  i.after   the value AFTER the call returns -> did fn_leave restore anything?

⚠️ zb ONLY. This is a claim about this tree's own implementation, not about
MSX-BASIC, so there is no oracle and none is pretended.

🔴 The `CLS` in the capture line is load-bearing: without it the line's own ECHO
carries the `[...]` fence and every row returns its own SOURCE TEXT (the shipped
gate's own note, eleven rows).
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "zerobas", "probes", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

ROWS = {
    # a literal body: nothing the FN does can matter
    'i.const':   (['DEFINT A-Z', 'DEF FNA(X)=7'], 'FNA(2)', '7'),
    # the SAME program with no DEFINT: FN_RTYPE is 8, not 2
    'i.noco':    (['DEF FNA(X)=7'], 'FNA(2)', '7'),
    # `%` on the FUNCTION only -- FN_RTYPE=2, formal type 8
    'i.pctfn':   (['DEF FNA%(X)=7'], 'FNA%(2)', '7'),
    # `%` on the FORMAL only -- FN_RTYPE=8, formal type 2
    'i.pctform': (['DEF FNA(X%)=X%'], 'FNA(2)', '2'),
    # the formal itself, DEFINT: is the slot readable at all?
    'i.formal':  (['DEFINT A-Z', 'DEF FNA(X)=X'], 'FNA(9)', '9'),
    # where the shadow lives, and what is in it
    'i.varptr':  (['DEFINT A-Z', 'DEF FNA(X)=VARPTR(X)'], 'FNA(9)', '-5483'),
    'i.peek':    (['DEFINT A-Z', 'DEF FNA(X)=PEEK(VARPTR(X))'], 'FNA(9)', '9'),
    # a control: the same expression with no FN in it
    'i.ctl':     (['DEFINT A-Z', 'X=9'], 'X', '9'),
    # what the frame looks like AFTER the call returned
    'i.after':   (['DEFINT A-Z', 'DEF FNA(X)=7', 'Y=FNA(2)'], 'PEEK(&HEAF5)', '146'),
}

BR = re.compile(r"\[([^\]]*)\]")
ERRRE = re.compile(r"(Undefined user function|Illegal function call|"
                   r"Type mismatch|Overflow|Illegal direct|Out of memory|"
                   r"[A-Z][A-Za-z' ]{2,25} error)")


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    txt = "".join(cap)
    m = BR.search(txt)
    if m:
        return " ".join(m.group(1).split()) or "<empty>"
    e = ERRRE.search(txt)
    return f"<{e.group(1).strip()}>" if e else "<NO OUTPUT>"


def main() -> int:
    width = max(len(k) for k in ROWS)
    bad = 0
    for label in sorted(ROWS):
        setup, expr, want = ROWS[label]
        lines = ["10 ON ERROR GOTO 900"]
        lines += [f"{20 + 10 * k} {ln}" for k, ln in enumerate(setup)]
        lines += [f'60 CLS:PRINT"[";{expr};"]":END']
        lines += ['900 CLS:PRINT"[ERR";ERR;"AT";ERL;"]":END']
        caps = omsx_repl.run_cases(ZB_M, [("direct", ["NEW"] + lines + ["RUN"])],
                                   batch=False, boot=8.0, step=8.0,
                                   cap_gap=10.0, timeout=300.0)
        got = face(caps[0])
        tag = "ok  " if got == want else "DIFF"
        if got != want:
            bad += 1
        print(f"{tag} {label:<{width}}  want={want!r}  zb={got!r}")
    print(f"ROWS: {len(ROWS)} printed, {len(ROWS)} scored — {bad} divergent")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
