#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G7 sprites black-box characterization, round 4 (VG-8020) -- residuals.

  F1  EC bit cleared again when a later PUT with an OMITTED colour uses x>=0
  F2  SCREEN 2 attribute-table init values: colour = literal 15 or FORCLR?
      and are all 32 planes initialised the same way (y=209, x=0, pat=plane)?
  F3  SCREEN 1: is the sprite attribute table also at $1B00?
  F4  SPRITE$(255) in 16x16 mode -- $3800+255*32 is past 16 KB; where does it land?
  F5  reading SPRITE$(n) in SCREEN 0 (writing there is ERR 5)
"""
from __future__ import annotations
import os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
SATR = 0x1B00
SPAT = 0x3800


def vdump(base_expr: str, n: int, tag: int, extra: str = "") -> list[str]:
    return [f'A$="":FOR I=0 TO {n-1}:A$=A$+STR$(VPEEK({base_expr}+I)):NEXT',
            f'SCREEN0:PRINT"Q{tag}Q";A$;"|";{extra or "0"}']


def _pick(txt: str, tag: int) -> str:
    m = re.search(rf"Q{tag}Q([^\r\n]*)", txt or "")
    return " ".join(m.group(1).split()) if m else f"<none> raw={(txt or '')[:70]!r}"


# (label, program-head, dump-base, count, extra)
F_CASES = [
    ("ec_clear",   "SCREEN2:PUT SPRITE 0,(-5,20),4,1:PUT SPRITE 0,(60,20)",
     f"&H{SATR:04X}", 4, ""),
    ("ec_clear2",  "SCREEN2:PUT SPRITE 0,(-5,20),4,1:PUT SPRITE 0,(60,20),,1",
     f"&H{SATR:04X}", 4, ""),
    ("init_col4",  "COLOR4,1,1:SCREEN2", f"&H{SATR:04X}", 8, "PEEK(&HF3E9)"),
    ("init_col15", "COLOR15,1,1:SCREEN2", f"&H{SATR:04X}", 8, "PEEK(&HF3E9)"),
    ("init_p8",    "SCREEN2", f"&H{SATR:04X}+4*8", 4, ""),
    ("init_p31",   "SCREEN2", f"&H{SATR:04X}+4*31", 4, ""),
    ("scr1_attr",  "SCREEN1:PUT SPRITE 0,(10,20),4,1", f"&H{SATR:04X}", 4, ""),
    ("scr1_init",  "SCREEN1", f"&H{SATR:04X}", 8, ""),
    ("s2_spr255a", "CLEAR 2000:SCREEN2,2:SPRITE$(255)=STRING$(32,170)",
     "&H17E0", 8, ""),          # ($3800 + 255*32) & $3FFF
    ("s2_spr255b", "CLEAR 2000:SCREEN2,2:SPRITE$(255)=STRING$(32,170)",
     f"&H{SPAT:04X}", 8, ""),   # ... or clamped back to pattern 0?
    ("s2_spr200",  "CLEAR 2000:SCREEN2,2:SPRITE$(200)=STRING$(32,170)",
     "&H0F00", 8, ""),          # ($3800 + 200*32) & $3FFF = $0F00
]


def f_all():
    print("=== F  round-4 residuals ===")
    specs = [("stored", [head] + vdump(base, n, i, extra))
             for i, (lab, head, base, n, extra) in enumerate(F_CASES)]
    outs = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for i, (c, o) in enumerate(zip(F_CASES, outs)):
        print(f"  {c[0]:12s} {c[1]:52s} @{c[2]:12s} -> {_pick(o, i)}")


F5_CASES = [
    ("read_scr0",  ["SCREEN0", 'B$=SPRITE$(0)']),
    ("read_scr1",  ["SCREEN1", 'B$=SPRITE$(0)']),
    ("read_n256",  ["SCREEN2", 'B$=SPRITE$(256)']),
    ("read_n255",  ["SCREEN2", 'B$=SPRITE$(255)']),
    ("read_neg",   ["SCREEN2", 'B$=SPRITE$(-1)']),
    ("assign_mid", ["SCREEN2", 'MID$(SPRITE$(0),1,1)="A"']),
    ("print_spr",  ["SCREEN2", 'A=LEN(SPRITE$(0))']),
]


def f5_read():
    print("\n=== F5  SPRITE$ read forms (K=ok, E<n>=err) ===")
    progs = [("stored", ["ON ERROR GOTO 40", ":".join(body),
                         'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'])
             for lab, body in F5_CASES]
    outs = omsx_repl.run_cases(REF, progs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for (lab, body), o in zip(F5_CASES, outs):
        toks = [ln.split()[0:2] for ln in (o or "").splitlines()
                if ln.strip().startswith(("K", "E"))]
        print(f"  {lab:12s} {':'.join(body):34s} -> {toks[:1]}")


if __name__ == "__main__":
    which = sys.argv[1:] or ["f", "f5"]
    if "f" in which:
        f_all()
    if "f5" in which:
        f5_read()
