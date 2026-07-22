#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G7 round 5 — the last two impl-blocking questions.

  G1  does `PUT SPRITE` / `SPRITE$=` stamp the SHARED graphics attribute ATRBYT
      ($F3F2, G6 D-G6-3)? The tenant dispatcher stamps it for every op that
      carries a colour, so ops 7/8 must be included or excluded on measured
      fact, not taste. Measured indirectly: a colourless PSET after a coloured
      PUT SPRITE draws in ATRBYT.
  G2  grammar leftovers: bare `SPRITE`, `SPRITE ON` in SCREEN 0, `PUT SPRITE`
      with a trailing comma, and where the plane/comma syntax line is.
"""
from __future__ import annotations
import os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")

# G1: ATRBYT after each statement, plus the colour a colourless PSET then draws.
G1_CASES = [
    ("baseline",   "COLOR15,1,1:SCREEN2"),
    ("after_put",  "COLOR15,1,1:SCREEN2:PUT SPRITE 0,(10,20),4,1"),
    ("after_put0", "COLOR15,1,1:SCREEN2:PUT SPRITE 0,(10,20)"),
    ("after_spr",  "COLOR15,1,1:SCREEN2:SPRITE$(0)=CHR$(255)"),
    ("after_line", "COLOR15,1,1:SCREEN2:LINE(0,0)-(3,3),7"),   # control: known to stamp
]


def g1_atrbyt():
    print("=== G1  ATRBYT ($F3F2) after sprite statements (control: LINE stamps 7) ===")
    specs = [("stored", [head, f'SCREEN0:PRINT"Q{i}Q";PEEK(&HF3F2)'])
             for i, (lab, head) in enumerate(G1_CASES)]
    outs = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",), capture="screen")
    for i, (c, o) in enumerate(zip(G1_CASES, outs)):
        m = re.search(rf"Q{i}Q([^\r\n]*)", o or "")
        print(f"  {c[0]:11s} {c[1]:44s} -> ATRBYT={m.group(1).split()[0] if m else '?'}")


G2_CASES = [
    ("bare_sprite",  ["SCREEN2", "SPRITE"]),
    ("sprite_scr0",  ["SCREEN0", "SPRITE ON"]),
    ("put_trail",    ["SCREEN2", "PUT SPRITE 0,(10,20),4,1,"]),
    ("put_5args",    ["SCREEN2", "PUT SPRITE 0,(10,20),4,1,9"]),
    ("put_nocomma",  ["SCREEN2", "PUT SPRITE 0 (10,20)"]),
    ("put_onlycomma",["SCREEN2", "PUT SPRITE 0,"]),
    ("put_step_only",["SCREEN2", "PUT SPRITE 0,STEP(10,20)"]),
    ("spr_nopar",    ["SCREEN2", 'SPRITE$0=CHR$(1)']),
    ("spr_noeq",     ["SCREEN2", 'SPRITE$(0)']),
    ("spr_scr1_wr",  ["SCREEN1", 'SPRITE$(0)=CHR$(1)']),
    ("put_lowercase",["SCREEN2", "put sprite 0,(10,20),4,1"]),
]


def g2_grammar():
    print("\n=== G2  grammar leftovers (K=ok, E<n>=err) ===")
    progs = [("stored", ["ON ERROR GOTO 40", ":".join(body),
                         'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'])
             for lab, body in G2_CASES]
    outs = omsx_repl.run_cases(REF, progs, batch=True, reset=("NEW",), capture="screen")
    for (lab, body), o in zip(G2_CASES, outs):
        toks = [ln.split()[0:2] for ln in (o or "").splitlines()
                if ln.strip().startswith(("K", "E"))]
        print(f"  {lab:14s} {':'.join(body):36s} -> {toks[:1]}")


if __name__ == "__main__":
    which = sys.argv[1:] or ["g1", "g2"]
    if "g1" in which:
        g1_atrbyt()
    if "g2" in which:
        g2_grammar()
