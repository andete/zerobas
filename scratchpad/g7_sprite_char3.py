#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G7 sprites black-box characterization, round 3 (VG-8020).

Closes the round-2 anomalies, ISOLATED (boot-per-case where VRAM carry-over
could confound: the sprite tables live in VRAM and survive `NEW`, so a batched
case inherits the previous case's attribute bytes unless SCREEN re-init wipes
them).

  E1 default -- what an OMITTED colour / pattern / coordinate resolves to
                (round 2 hint: "keep the existing attribute byte", but a bare
                negative-x case returned colour $86 = EC|6, which that rule does
                not explain). Isolated, fresh boot, one statement each.
  E2 ec      -- the early-clock rule for x<0 across a sweep
  E3 domain  -- 16x16 (SCREEN 2,2) SPRITE$ n domain + PUT SPRITE pattern domain
  E4 misc    -- does PUT SPRITE need SPRITE ON; float/expr args; ordering
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


# ---- E1: omitted-argument defaults, ISOLATED --------------------------------
E1_CASES = [
    ("fresh_full",   "PUT SPRITE 0,(10,20),4,1"),
    ("fresh_nocol",  "PUT SPRITE 0,(10,20),,1"),
    ("fresh_nopat",  "PUT SPRITE 0,(10,20),4"),
    ("fresh_neither","PUT SPRITE 0,(10,20)"),
    ("negx_full",    "PUT SPRITE 0,(-5,20),4,1"),
    ("negx_nocol",   "PUT SPRITE 0,(-5,20)"),
    ("negx_nocol2",  "PUT SPRITE 0,(-5,20),,1"),
    ("col4_default", "COLOR4:PUT SPRITE 0,(10,20)"),
    ("col4_negx",    "COLOR4:PUT SPRITE 0,(-5,20)"),
    ("after9_nocol", "PUT SPRITE 0,(10,20),9,1:PUT SPRITE 0,(30,40)"),
    ("after9_negx",  "PUT SPRITE 0,(10,20),9,1:PUT SPRITE 0,(-5,40)"),
    ("nocoord_fresh","PUT SPRITE 0,,4,1"),
    ("nocoord_pset", "PSET(50,60):PUT SPRITE 0,,4,1"),
    ("nocoord_after","PUT SPRITE 0,(70,80),4,1:PUT SPRITE 0,,9,2"),
    ("plane1_fresh", "PUT SPRITE 1,(10,20)"),
    ("plane5_fresh", "PUT SPRITE 5,(10,20)"),
]


def e1_defaults():
    print("=== E1  omitted-arg defaults, BOOT-PER-CASE (y x pat col | grpac gx) ===")
    work = ('PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA);PEEK(&HF3E9)')
    specs = []
    for i, (lab, stmt) in enumerate(E1_CASES):
        plane = 5 if lab.startswith("plane5") else (1 if lab.startswith("plane1") else 0)
        specs.append(("stored", [f"CLEAR 2000:SCREEN2:{stmt}"]
                      + vdump(f"&H{SATR:04X}+4*{plane}", 4, i, work)))
    outs = omsx_repl.run_cases(REF, specs, batch=False, capture="screen", cart=None)
    for i, (c, o) in enumerate(zip(E1_CASES, outs)):
        print(f"  {c[0]:14s} {c[1]:44s} -> {_pick(o, i)}")


# ---- E2: early-clock sweep --------------------------------------------------
E2_XS = [-64, -40, -33, -32, -31, -16, -1, 0, 1, 31, 32, 200, 255, 256, 511, 512]


def e2_ec():
    print("\n=== E2  x sweep -> (attr x, colour byte) with colour 4 ===")
    specs = [("stored", [f"CLEAR 2000:SCREEN2:PUT SPRITE 0,({x},20),4,1"]
              + vdump(f"&H{SATR:04X}", 4, i))
             for i, x in enumerate(E2_XS)]
    outs = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for i, (x, o) in enumerate(zip(E2_XS, outs)):
        print(f"  x={x:6d} -> {_pick(o, i)}")


# ---- E3: 16x16 domains ------------------------------------------------------
E3_CASES = [
    ("s2_spr63",   "SCREEN2,2", 'SPRITE$(63)=CHR$(1)'),
    ("s2_spr64",   "SCREEN2,2", 'SPRITE$(64)=CHR$(1)'),
    ("s2_spr255",  "SCREEN2,2", 'SPRITE$(255)=CHR$(1)'),
    ("s2_spr256",  "SCREEN2,2", 'SPRITE$(256)=CHR$(1)'),
    ("s2_put63",   "SCREEN2,2", "PUT SPRITE 0,(10,20),4,63"),
    ("s2_put64",   "SCREEN2,2", "PUT SPRITE 0,(10,20),4,64"),
    ("s2_put255",  "SCREEN2,2", "PUT SPRITE 0,(10,20),4,255"),
    ("s2_put256",  "SCREEN2,2", "PUT SPRITE 0,(10,20),4,256"),
    ("s0_put255",  "SCREEN2,0", "PUT SPRITE 0,(10,20),4,255"),
    ("s0_put256",  "SCREEN2,0", "PUT SPRITE 0,(10,20),4,256"),
    ("s2_plane31", "SCREEN2,2", "PUT SPRITE 31,(10,20),4,1"),
    ("s2_plane32", "SCREEN2,2", "PUT SPRITE 32,(10,20),4,1"),
    # float / expression args
    ("float_pat",  "SCREEN2",   "PUT SPRITE 0,(10.7,20.2),4.9,1.9"),
    ("float_spr",  "SCREEN2",   'SPRITE$(1.9)=CHR$(1)'),
    ("expr",       "SCREEN2",   "A=3:PUT SPRITE A-3,(A*4,20),A+1,A"),
    # does anything need SPRITE ON?
    ("spron",      "SCREEN2",   "SPRITE ON:PUT SPRITE 0,(10,20),4,1"),
    ("sproff",     "SCREEN2",   "SPRITE OFF:PUT SPRITE 0,(10,20),4,1"),
]


def e3_domains():
    print("\n=== E3  domains / coercion (K=ok, E<n>=err) ===")
    progs = [("stored", ["ON ERROR GOTO 40", f"{s}:{stmt}",
                         'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'])
             for lab, s, stmt in E3_CASES]
    outs = omsx_repl.run_cases(REF, progs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for (lab, s, stmt), o in zip(E3_CASES, outs):
        toks = [ln.split()[0:2] for ln in (o or "").splitlines()
                if ln.strip().startswith(("K", "E"))]
        print(f"  {lab:12s} {s:10s} {stmt:36s} -> {toks[:1]}")


# ---- E4: float coercion values ---------------------------------------------
E4_CASES = [
    ("round_coords", "PUT SPRITE 0,(10.7,20.2),4.9,1.9"),
    ("neg_frac",     "PUT SPRITE 0,(-5.7,20),4,1"),
    ("expr_plane",   "A=3:PUT SPRITE A-3,(A*4,20),A+1,A"),
]


def e4_coerce():
    print("\n=== E4  float/expr coercion -> attribute bytes ===")
    specs = [("stored", [f"CLEAR 2000:SCREEN2:{stmt}"] + vdump(f"&H{SATR:04X}", 4, i))
             for i, (lab, stmt) in enumerate(E4_CASES)]
    outs = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for i, (c, o) in enumerate(zip(E4_CASES, outs)):
        print(f"  {c[0]:14s} {c[1]:44s} -> {_pick(o, i)}")


if __name__ == "__main__":
    which = sys.argv[1:] or ["e1", "e2", "e3", "e4"]
    if "e1" in which:
        e1_defaults()
    if "e2" in which:
        e2_ec()
    if "e3" in which:
        e3_domains()
    if "e4" in which:
        e4_coerce()
