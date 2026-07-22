#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G7 sprites black-box characterization on the Philips VG-8020, round 1.

Read-only investigation (nothing asserted): DUMP reference SPRITE$ / PUT SPRITE
behaviour so the G7 pins can be written from measured fact (the recurring arc
lesson). Pure black box -- no ROM disassembly. Mirrors g6_draw_char1.py.

METHOD: sprites are a *VRAM table write* problem, not a rasteriser problem, so
everything is measured by reading the tables back with VPEEK while still in
SCREEN 2, stashing the bytes in a string, then printing in SCREEN 0. No bitmap
capture, no boot-per-case.

  C1 tokens  -- crunch of SPRITE$ / PUT SPRITE / SPRITE ON|OFF|STOP forms
  C2 pattern -- SPRITE$(n)= writes: pattern-table bytes, padding/truncation,
                n domain, size 0 (8x8) vs size 1 (16x16), read-back LEN
  C3 attrib  -- PUT SPRITE writes into the sprite attribute table: arg defaults,
                omitted args, y=208/209, negative coords, colour, pattern no.
  C4 errors  -- domain/limit errors for both statements
"""
from __future__ import annotations
import os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
TXTTAB = 0xF676

# SCREEN 2 table bases (spec §11 [PIN]): sprite attribute $1B00, pattern $3800
SATR = 0x1B00
SPAT = 0x3800


def vdump(base_expr: str, n: int, tag: int, extra: str = "") -> list[str]:
    """BASIC lines that stash n VRAM bytes from base into A$ then print tagged.
    Stays in the graphics mode for the VPEEK, prints after SCREEN 0."""
    return [f'A$="":FOR I=0 TO {n-1}:A$=A$+STR$(VPEEK({base_expr}+I)):NEXT',
            f'SCREEN0:PRINT"Q{tag}Q";A$;"|";{extra or "0"}']


def _pick(txt: str, tag: int) -> str:
    m = re.search(rf"Q{tag}Q([^\r\n]*)", txt or "")
    return " ".join(m.group(1).split()) if m else f"<none> raw={(txt or '')[:70]!r}"


# ---- C1: token crunch -------------------------------------------------------
C1 = [
    'sprite$(0)="ab"',
    'a$=sprite$(0)',
    'put sprite 0,(10,20),4,1',
    'put sprite 0,(10,20)',
    'put sprite 0,step(10,20),4,1',
    'sprite on',
    'sprite off',
    'sprite stop',
    'on sprite gosub 100',
]


def c1_tokens():
    print("=== C1  sprite token crunch (grammar) ===")
    specs = [("direct", [f"1 {b}"]) for b in C1]
    raws = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture=("stored_line", TXTTAB), cart=None)
    for b, raw in zip(C1, raws):
        rb = bytes.fromhex(raw) if raw else b""
        body = rb[4:] if len(rb) >= 5 else b""
        s = " ".join(f"{x:02X}" for x in body) if body else "<not stored>"
        print(f"  {b:28s} -> {s}")


# ---- C2: SPRITE$ pattern writes --------------------------------------------
# (label, screen-setup, statement, dump-base, dump-count, extra-print)
C2_CASES = [
    ("8x8_1byte",   "SCREEN2",   'SPRITE$(0)=CHR$(255)',              f"&H{SPAT:04X}", 10, ""),
    ("8x8_8byte",   "SCREEN2",   'SPRITE$(0)=STRING$(8,170)',         f"&H{SPAT:04X}", 10, ""),
    ("8x8_12byte",  "SCREEN2",   'SPRITE$(0)=STRING$(12,170)',        f"&H{SPAT:04X}", 14, ""),
    ("8x8_32byte",  "SCREEN2",   'SPRITE$(0)=STRING$(32,170)',        f"&H{SPAT:04X}", 10, ""),
    ("8x8_empty",   "SCREEN2",   'SPRITE$(0)=""',                     f"&H{SPAT:04X}", 10, ""),
    ("8x8_n1",      "SCREEN2",   'SPRITE$(1)=STRING$(8,204)',         f"&H{SPAT+8:04X}", 10, ""),
    ("8x8_n255",    "SCREEN2",   'SPRITE$(255)=STRING$(8,204)',       f"&H{SPAT+255*8:04X}", 8, ""),
    ("8x8_readlen", "SCREEN2",   'SPRITE$(0)=CHR$(255):B$=SPRITE$(0)', f"&H{SPAT:04X}", 2, "LEN(B$)"),
    ("8x8_readval", "SCREEN2",   'SPRITE$(0)=STRING$(8,170):B$=SPRITE$(0)', f"&H{SPAT:04X}", 2,
     "ASC(B$);ASC(MID$(B$,8,1))"),
    # size 1 = 16x16 (SCREEN 2,1); size 2/3 = magnified
    ("16x16_1byte", "SCREEN2,1", 'SPRITE$(0)=CHR$(255)',              f"&H{SPAT:04X}", 34, ""),
    ("16x16_32b",   "SCREEN2,1", 'SPRITE$(0)=STRING$(32,170)',        f"&H{SPAT:04X}", 34, ""),
    ("16x16_8b",    "SCREEN2,1", 'SPRITE$(0)=STRING$(8,170)',         f"&H{SPAT:04X}", 34, ""),
    ("16x16_n1",    "SCREEN2,1", 'SPRITE$(1)=STRING$(32,204)',        f"&H{SPAT+32:04X}", 34, ""),
    ("16x16_rdlen", "SCREEN2,1", 'SPRITE$(0)=CHR$(255):B$=SPRITE$(0)', f"&H{SPAT:04X}", 2, "LEN(B$)"),
    ("mag2_len",    "SCREEN2,2", 'SPRITE$(0)=CHR$(255):B$=SPRITE$(0)', f"&H{SPAT:04X}", 2, "LEN(B$)"),
    ("mag3_len",    "SCREEN2,3", 'SPRITE$(0)=CHR$(255):B$=SPRITE$(0)', f"&H{SPAT:04X}", 2, "LEN(B$)"),
    # does SPRITE$ work outside SCREEN 2? (table base differs per mode)
    ("scr1_write",  "SCREEN1",   'SPRITE$(0)=STRING$(8,170)',         f"&H{SPAT:04X}", 10, ""),
    ("scr0_write",  "SCREEN0",   'SPRITE$(0)=STRING$(8,170)',         f"&H{SPAT:04X}", 10, ""),
]


def c2_patterns():
    print("\n=== C2  SPRITE$(n)= pattern-table writes ===")
    specs = []
    for i, (lab, setup, stmt, base, n, extra) in enumerate(C2_CASES):
        specs.append(("stored", [f"{setup}:{stmt}"] + vdump(base, n, i, extra)))
    outs = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for i, (c, o) in enumerate(zip(C2_CASES, outs)):
        print(f"  {c[0]:12s} {c[1]:10s} {c[2]:42s} -> {_pick(o, i)}")


# ---- C3: PUT SPRITE attribute writes ---------------------------------------
# attribute entry = 4 bytes per plane at $1B00 + 4n
C3_CASES = [
    ("full",        "SCREEN2", "PUT SPRITE 0,(10,20),4,1",      0),
    ("plane3",      "SCREEN2", "PUT SPRITE 3,(10,20),4,1",      3),
    ("no_pattern",  "SCREEN2", "PUT SPRITE 0,(10,20),4",        0),
    ("no_colour",   "SCREEN2", "PUT SPRITE 0,(10,20),,7",       0),
    ("coords_only", "SCREEN2", "PUT SPRITE 0,(10,20)",          0),
    ("y208",        "SCREEN2", "PUT SPRITE 0,(10,208),4,1",     0),
    ("y209",        "SCREEN2", "PUT SPRITE 0,(10,209),4,1",     0),
    ("y_neg1",      "SCREEN2", "PUT SPRITE 0,(10,-1),4,1",      0),
    ("y_255",       "SCREEN2", "PUT SPRITE 0,(10,255),4,1",     0),
    ("x_neg1",      "SCREEN2", "PUT SPRITE 0,(-1,20),4,1",      0),
    ("x_neg32",     "SCREEN2", "PUT SPRITE 0,(-32,20),4,1",     0),
    ("x_255",       "SCREEN2", "PUT SPRITE 0,(255,20),4,1",     0),
    ("colour0",     "SCREEN2", "PUT SPRITE 0,(10,20),0,1",      0),
    ("colour15",    "SCREEN2", "PUT SPRITE 0,(10,20),15,1",     0),
    ("pat255",      "SCREEN2", "PUT SPRITE 0,(10,20),4,255",    0),
    ("plane31",     "SCREEN2", "PUT SPRITE 31,(10,20),4,1",     31),
    ("step",        "SCREEN2", "PSET(50,60):PUT SPRITE 0,STEP(10,20),4,1", 0),
    ("s16_pat1",    "SCREEN2,1", "PUT SPRITE 0,(10,20),4,1",    0),
    ("s16_pat2",    "SCREEN2,1", "PUT SPRITE 0,(10,20),4,2",    0),
]


def c3_attribs():
    print("\n=== C3  PUT SPRITE -> attribute table (y x pat colour) ===")
    specs = []
    for i, (lab, setup, stmt, plane) in enumerate(C3_CASES):
        base = f"&H{SATR:04X}+4*{plane}"
        specs.append(("stored", [f"{setup}:{stmt}"] + vdump(base, 4, i,
                      'PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA)')))
    outs = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for i, (c, o) in enumerate(zip(C3_CASES, outs)):
        print(f"  {c[0]:12s} {c[2]:46s} -> {_pick(o, i)}")


# ---- C4: errors -------------------------------------------------------------
C4_CASES = [
    ("spr_n256",    ["SCREEN2", 'SPRITE$(256)=CHR$(1)']),
    ("spr_n_1",     ["SCREEN2", 'SPRITE$(-1)=CHR$(1)']),
    ("spr_n64_16",  ["SCREEN2,1", 'SPRITE$(64)=CHR$(1)']),
    ("spr_n63_16",  ["SCREEN2,1", 'SPRITE$(63)=CHR$(1)']),
    ("spr_n255_16", ["SCREEN2,1", 'SPRITE$(255)=CHR$(1)']),
    ("spr_num",     ["SCREEN2", 'SPRITE$(0)=5']),
    ("spr_scr0",    ["SCREEN0", 'SPRITE$(0)=CHR$(1)']),
    ("spr_read0",   ["SCREEN2", 'B$=SPRITE$(0)']),
    ("put_p32",     ["SCREEN2", "PUT SPRITE 32,(10,20),4,1"]),
    ("put_p_1",     ["SCREEN2", "PUT SPRITE -1,(10,20),4,1"]),
    ("put_c16",     ["SCREEN2", "PUT SPRITE 0,(10,20),16,1"]),
    ("put_c_1",     ["SCREEN2", "PUT SPRITE 0,(10,20),-1,1"]),
    ("put_pat256",  ["SCREEN2", "PUT SPRITE 0,(10,20),4,256"]),
    ("put_pat64_16",["SCREEN2,1", "PUT SPRITE 0,(10,20),4,64"]),
    ("put_pat_1",   ["SCREEN2", "PUT SPRITE 0,(10,20),4,-1"]),
    ("put_x300",    ["SCREEN2", "PUT SPRITE 0,(300,20),4,1"]),
    ("put_x40000",  ["SCREEN2", "PUT SPRITE 0,(40000,20),4,1"]),
    ("put_y300",    ["SCREEN2", "PUT SPRITE 0,(10,300),4,1"]),
    ("put_scr0",    ["SCREEN0", "PUT SPRITE 0,(10,20),4,1"]),
    ("put_scr1",    ["SCREEN1", "PUT SPRITE 0,(10,20),4,1"]),
    ("put_bare",    ["SCREEN2", "PUT SPRITE 0"]),
    ("put_nocoord", ["SCREEN2", "PUT SPRITE 0,,4,1"]),
    ("spr_on",      ["SCREEN2", "SPRITE ON"]),
    ("spr_off",     ["SCREEN2", "SPRITE OFF"]),
    ("spr_stop",    ["SCREEN2", "SPRITE STOP"]),
]


def c4_errors():
    print("\n=== C4  errors / edges (K=ok, E<n>=err) ===")
    progs = []
    for lab, body in C4_CASES:
        progs.append(("stored", ["ON ERROR GOTO 40", ":".join(body),
                                 'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END']))
    outs = omsx_repl.run_cases(REF, progs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for (lab, body), o in zip(C4_CASES, outs):
        toks = [ln.strip() for ln in (o or "").splitlines()
                if ln.strip().startswith("K") or ln.strip().startswith("E")]
        print(f"  {lab:13s} {':'.join(body):34s} -> {toks}")


if __name__ == "__main__":
    which = sys.argv[1:] or ["c1", "c2", "c3", "c4"]
    if "c1" in which:
        c1_tokens()
    if "c2" in which:
        c2_patterns()
    if "c3" in which:
        c3_attribs()
    if "c4" in which:
        c4_errors()
