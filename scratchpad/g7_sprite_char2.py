#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G7 sprites black-box characterization, round 2 (VG-8020).

Round 1 fixed the shape; round 2 closes the open questions it raised:

  D1 size    -- SCREEN 2,<s>: s=0/1 are 8x8 (8-byte patterns), s=2/3 are 16x16
                (32-byte). Re-run the 16x16 matrix with s=2, incl. the SPRITE$ n
                domain and the PUT SPRITE *pattern number* mapping (does BASIC
                store n or 4n in the attribute byte?).
  D2 coords  -- what lands in the attribute bytes for x/y > 255 (round 1: no error)
  D3 default -- omitted colour: FORCLR? previous attribute colour? and the EC bit
  D4 omitted -- `PUT SPRITE n,,c,p` (accepted!): which coords does it use?
  D5 state   -- attribute-table contents after SCREEN 2 / CLS; RG1SAV size+mag bits
  D6 work    -- GXPOS/GYPOS as well as GRPACX/Y after PUT SPRITE
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
    # CLEAR 2000: the dump string plus the case's own strings must fit -- the
    # default 200-byte string space overflows on a 34-byte VRAM dump.
    return [f'A$="":FOR I=0 TO {n-1}:A$=A$+STR$(VPEEK({base_expr}+I)):NEXT',
            f'SCREEN0:PRINT"Q{tag}Q";A$;"|";{extra or "0"}']


def _pick(txt: str, tag: int) -> str:
    m = re.search(rf"Q{tag}Q([^\r\n]*)", txt or "")
    return " ".join(m.group(1).split()) if m else f"<none> raw={(txt or '')[:70]!r}"


def _run(specs):
    return omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)


# ---- D1: 16x16 mode (SCREEN 2,2) -------------------------------------------
D1_CASES = [
    ("s2_1byte",   "SCREEN2,2", 'SPRITE$(0)=CHR$(255)',           f"&H{SPAT:04X}", 34, ""),
    ("s2_32byte",  "SCREEN2,2", 'SPRITE$(0)=STRING$(32,170)',     f"&H{SPAT:04X}", 34, ""),
    ("s2_40byte",  "SCREEN2,2", 'SPRITE$(0)=STRING$(40,170)',     f"&H{SPAT:04X}", 34, ""),
    ("s2_n1",      "SCREEN2,2", 'SPRITE$(1)=STRING$(32,204)',     f"&H{SPAT+32:04X}", 34, ""),
    ("s2_n63",     "SCREEN2,2", 'SPRITE$(63)=STRING$(32,204)',    f"&H{SPAT+63*32:04X}", 32, ""),
    ("s2_rdlen",   "SCREEN2,2", 'SPRITE$(0)=CHR$(9):B$=SPRITE$(0)', f"&H{SPAT:04X}", 2, "LEN(B$)"),
    ("s3_rdlen",   "SCREEN2,3", 'SPRITE$(0)=CHR$(9):B$=SPRITE$(0)', f"&H{SPAT:04X}", 2, "LEN(B$)"),
    # PUT SPRITE pattern-number mapping in 16x16 mode
    ("s2_put_p0",  "SCREEN2,2", "PUT SPRITE 0,(10,20),4,0",       f"&H{SATR:04X}", 4, ""),
    ("s2_put_p1",  "SCREEN2,2", "PUT SPRITE 0,(10,20),4,1",       f"&H{SATR:04X}", 4, ""),
    ("s2_put_p2",  "SCREEN2,2", "PUT SPRITE 0,(10,20),4,2",       f"&H{SATR:04X}", 4, ""),
    ("s2_put_p63", "SCREEN2,2", "PUT SPRITE 0,(10,20),4,63",      f"&H{SATR:04X}", 4, ""),
    # 8x8 mode for contrast (round 1 said pattern byte = n)
    ("s0_put_p2",  "SCREEN2,0", "PUT SPRITE 0,(10,20),4,2",       f"&H{SATR:04X}", 4, ""),
]


def d1_size():
    print("=== D1  16x16 sprite size (SCREEN 2,2 / 2,3) ===")
    specs = [("stored", [f"CLEAR 2000:{s}:{stmt}"] + vdump(base, n, i, extra))
             for i, (lab, s, stmt, base, n, extra) in enumerate(D1_CASES)]
    for i, (c, o) in enumerate(zip(D1_CASES, _run(specs))):
        print(f"  {c[0]:11s} {c[1]:10s} {c[2]:40s} -> {_pick(o, i)}")


# ---- D2/D3/D4/D6: attribute-byte edge semantics -----------------------------
WORK = ('PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA);'
        'PEEK(&HFCB3)+256*PEEK(&HFCB4);PEEK(&HFCB5)+256*PEEK(&HFCB6)')

D2_CASES = [
    # x/y beyond a byte (round 1: NO error)
    ("x256",     "SCREEN2", "PUT SPRITE 0,(256,20),4,1"),
    ("x300",     "SCREEN2", "PUT SPRITE 0,(300,20),4,1"),
    ("y300",     "SCREEN2", "PUT SPRITE 0,(10,300),4,1"),
    ("x32767",   "SCREEN2", "PUT SPRITE 0,(32767,20),4,1"),
    ("x_1000",   "SCREEN2", "PUT SPRITE 0,(-1000,20),4,1"),
    ("x_33",     "SCREEN2", "PUT SPRITE 0,(-33,20),4,1"),
    # colour default vs FORCLR / previous attribute
    ("forclr4",  "SCREEN2", "COLOR4:PUT SPRITE 0,(10,20)"),
    ("prevcol",  "SCREEN2", "PUT SPRITE 0,(10,20),9,1:PUT SPRITE 0,(30,40)"),
    ("prevcol_c","SCREEN2", "PUT SPRITE 0,(10,20),9,1:COLOR6:PUT SPRITE 0,(30,40)"),
    ("negx_nocol","SCREEN2","PUT SPRITE 0,(-5,20)"),
    ("negx_then_pos","SCREEN2","PUT SPRITE 0,(-5,20),4,1:PUT SPRITE 0,(60,20),4,1"),
    # omitted coordinate forms
    ("nocoord",  "SCREEN2", "PSET(50,60):PUT SPRITE 0,,4,1"),
    ("nocoord2", "SCREEN2", "PUT SPRITE 0,(70,80),4,1:PUT SPRITE 0,,9,1"),
    ("halfcoord","SCREEN2", "PSET(50,60):PUT SPRITE 0,(,20),4,1"),
    ("halfcoord2","SCREEN2","PSET(50,60):PUT SPRITE 0,(10,),4,1"),
    ("stepchain","SCREEN2", "PUT SPRITE 0,(50,60),4,1:PUT SPRITE 0,STEP(5,5),4,1"),
]


def d2_attr_edges():
    print("\n=== D2/D3/D4  attribute-byte edges (y x pat col | grpacx y gxpos gypos) ===")
    # NOTE: no ON ERROR / second print line here -- each `SCREEN0` CLEARS the
    # screen, so a trailing status line wipes the dump (round-2 self-inflicted).
    specs = [("stored", [f"CLEAR 2000:{s}:{stmt}"]
              + vdump(f"&H{SATR:04X}", 4, i, WORK))
             for i, (lab, s, stmt) in enumerate(D2_CASES)]
    for i, (c, o) in enumerate(zip(D2_CASES, _run(specs))):
        print(f"  {c[0]:14s} {c[2]:44s} -> {_pick(o, i)}")


# ---- D5: table state after mode set / CLS ----------------------------------
D5_CASES = [
    ("after_scr2",  "SCREEN2", "", f"&H{SATR:04X}", 16),
    ("after_cls",   "SCREEN2", "PUT SPRITE 0,(10,20),4,1:CLS", f"&H{SATR:04X}", 8),
    ("scr2_again",  "SCREEN2", "PUT SPRITE 0,(10,20),4,1:SCREEN2", f"&H{SATR:04X}", 8),
    ("scr1_then2",  "SCREEN2", "PUT SPRITE 0,(10,20),4,1:SCREEN1:SCREEN2", f"&H{SATR:04X}", 8),
    ("pat_after_scr2", "SCREEN2", "SPRITE$(0)=STRING$(8,170):SCREEN2", f"&H{SPAT:04X}", 8),
    ("pat_after_cls",  "SCREEN2", "SPRITE$(0)=STRING$(8,170):CLS", f"&H{SPAT:04X}", 8),
]


def d5_state():
    print("\n=== D5  attribute/pattern table state after mode set / CLS "
          "(+RG1SAV $F3E0, FORCLR) ===")
    specs = []
    for i, (lab, s, stmt, base, n) in enumerate(D5_CASES):
        head = f"CLEAR 2000:{s}:{stmt}" if stmt else f"CLEAR 2000:{s}"
        specs.append(("stored", [head] + vdump(base, n, i, "PEEK(&HF3E0);PEEK(&HF3E9)")))
    for i, (c, o) in enumerate(zip(D5_CASES, _run(specs))):
        print(f"  {c[0]:16s} {c[2]:44s} -> {_pick(o, i)}")


# ---- D5b: RG1SAV per SCREEN 2,<s> ------------------------------------------
def d5b_rg1():
    print("\n=== D5b  RG1SAV ($F3E0) per SCREEN 2,<size> ===")
    cases = ["SCREEN2", "SCREEN2,0", "SCREEN2,1", "SCREEN2,2", "SCREEN2,3",
             "SCREEN2,2:SCREEN2", "SCREEN1,2", "SCREEN0"]
    specs = [("stored", [c, f'SCREEN0:PRINT"Q{i}Q";PEEK(&HF3E0);PEEK(&HF3E1)'])
             for i, c in enumerate(cases)]
    for i, (c, o) in enumerate(zip(cases, _run(specs))):
        print(f"  {c:16s} -> {_pick(o, i)}")


if __name__ == "__main__":
    which = sys.argv[1:] or ["d1", "d2", "d5", "d5b"]
    if "d1" in which:
        d1_size()
    if "d2" in which:
        d2_attr_edges()
    if "d5" in which:
        d5_state()
    if "d5b" in which:
        d5b_rg1()
