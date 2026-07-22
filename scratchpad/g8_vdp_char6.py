#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G8 characterization round 6 (Philips VG-8020): grammar edges.

The value/domain semantics are pinned (rounds 1-5).  What is left is the shape
of the statement: `VDP(n)=v` crunches as a FUNCTION token on the left of `=`
(round 1), so the interpreter must accept an assignment that starts with a
function token -- round 6 measures exactly how far that goes (LET form, bare
name, missing operand, list form) and which error each malformed shape raises.

Every case stays in SCREEN 0 and reports through memory, so it batches.
"""
from __future__ import annotations
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
RES = 0xD100
CAP = ("mem_abs", [(RES, 2)])

CASES = [
    ("let_vdp",    "LET VDP(0)=2"),
    ("let_base",   "LET BASE(0)=&H0400"),
    ("bare_vdp",   "VDP(0)"),
    ("bare_name",  "VDP=1"),
    ("bare_base",  "BASE=1"),
    ("no_rhs",     "VDP(0)="),
    ("no_paren",   "VDP 0=1"),
    ("two_args",   "VDP(0,1)=2"),
    ("list_rhs",   "VDP(0)=1,2"),
    ("self",       "VDP(0)=VDP(0)"),
    ("base_self",  "BASE(0)=BASE(0)"),
    ("read_bare",  "A=VDP"),
    ("read_nopar", "A=VDP 0"),
    ("str_val",    'VDP(0)="A"'),
    ("str_idx",    'VDP("A")=1'),
    ("str_base",   'BASE(0)="A"'),
    ("for_lhs",    "FOR VDP(0)=0 TO 1:NEXT"),
    ("swap_lhs",   "SWAP VDP(0),A"),
    ("mid_stmt",   "A=1:VDP(0)=2:B=3"),
    ("if_stmt",    "IF 1 THEN VDP(0)=2"),
]


def main() -> int:
    progs = [("stored", [
        "ON ERROR GOTO 50",
        f"POKE&H{RES:04X},255",
        f"SCREEN0:{stmt}",
        f"POKE&H{RES:04X},0:END",
        f"POKE&H{RES:04X},1:POKE&H{RES+1:04X},ERR:END",
    ]) for lab, stmt in CASES]
    outs = omsx_repl.run_cases(REF, progs, batch=True, reset=("NEW",),
                               capture=CAP, cart=None)
    print("=== H1  VDP / BASE grammar edges ===")
    for (lab, stmt), o in zip(CASES, outs):
        if not o:
            r = "<no capture>"
        else:
            b = bytes.fromhex(o)
            r = {255: "<not reached>", 0: "OK"}.get(b[0], f"ERR {b[1]}")
        print(f"  {lab:11s} {stmt:24s} -> {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
