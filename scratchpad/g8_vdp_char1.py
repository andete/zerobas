#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G8 `VDP(n)` / `BASE(n)=` black-box characterization on the Philips VG-8020.

Read-only investigation (nothing asserted): DUMP the reference behaviour of the
VDP-register pseudo-array `VDP(n)` (read AND write) and of `BASE(n)` assignment,
so the G8 pins can be written from measured fact (the recurring arc lesson).
Pure black box -- no ROM disassembly.

  C1 tokens  -- crunch of VDP(n) / VDP(n)= / BASE(n)= forms (token bytes)
  C2 vdpread -- PRINT VDP(n) across n and across SCREEN modes; n domain + errors
  C3 vdpwrite-- VDP(n)=v: read-back, the RAM shadow at $F3DF.., visible effect
  C4 baseread-- PRINT BASE(n) for n across all modes (what our BASE() must match)
  C5 basewr  -- BASE(n)=v: read-back, which RAM cell moves, when the VDP follows
"""
from __future__ import annotations
import os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
TXTTAB = 0xF676
RG0SAV = 0xF3DF          # published MSX work area: VDP R0..R7 write shadows
STATFL = 0xF3E7          # status-register copy maintained by the ISR


def _pick(txt: str, tag: str) -> str:
    m = re.search(rf"Q{tag}Q([^\r\n]*)", txt or "")
    return " ".join(m.group(1).split()) if m else f"<none> raw={(txt or '')[:60]!r}"


# ---- C1: token crunch -------------------------------------------------------
C1 = [
    'a=vdp(0)',
    'print vdp(1)',
    'vdp(1)=2',
    'vdp(0)=vdp(0)or2',
    'a=base(0)',
    'base(0)=&h1800',
    'print base(10)',
    'vdp(8)=1',
    'a=vdp(8)',
]


def c1_tokens():
    print("=== C1  VDP / BASE token crunch (grammar) ===")
    specs = [("direct", [f"1 {b}"]) for b in C1]
    raws = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture=("stored_line", TXTTAB), cart=None)
    for b, raw in zip(C1, raws):
        rb = bytes.fromhex(raw) if raw else b""
        body = rb[4:] if len(rb) >= 5 else b""
        s = " ".join(f"{x:02X}" for x in body) if body else "<not stored>"
        print(f"  {b:24s} -> {s}")


# ---- C2: VDP(n) read --------------------------------------------------------
# (label, setup, expression) -- printed with ON ERROR so a domain error shows.
C2_CASES = [(f"s{m}_n{n}", f"SCREEN{m}", f"VDP({n})")
            for m in (0, 1, 2)
            for n in (-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 255, 256)]
C2_CASES += [
    ("frac_n",   "SCREEN0", "VDP(1.7)"),
    ("expr_n",   "SCREEN0", "VDP(3-2)"),
    ("shadow1",  "SCREEN0", "PEEK(&HF3E0)"),   # RG1SAV, to pair with VDP(1)
    ("statfl",   "SCREEN0", "PEEK(&HF3E7)"),   # STATFL, to pair with VDP(8)
]


def c2_vdp_read():
    print("\n=== C2  VDP(n) read (value, or E<err>) ===")
    progs = [("stored", ["ON ERROR GOTO 40",
                         f"{s}:A={e}",
                         'SCREEN0:PRINT"Q";A:END',
                         'SCREEN0:PRINT"E";ERR:END'])
             for lab, s, e in C2_CASES]
    outs = omsx_repl.run_cases(REF, progs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for (lab, s, e), o in zip(C2_CASES, outs):
        hit = [ln.strip() for ln in (o or "").splitlines()
               if ln.strip().startswith(("Q", "E"))]
        print(f"  {lab:12s} {e:16s} -> {hit[:1]}")


# ---- C3: VDP(n)= write ------------------------------------------------------
# Each case: set a register, then report (read-back VDP(n), RAM shadow PEEK).
C3_CASES = [
    ("r1_e2",    "SCREEN0", "VDP(1)=VDP(1)OR32",  1),   # blink/irq bits
    ("r7_fg",    "SCREEN0", "VDP(7)=&H4F",        7),   # border/fg colour
    ("r0_set",   "SCREEN0", "VDP(0)=2",           0),
    ("r2_name",  "SCREEN2", "VDP(2)=&H06",        2),   # name table base
    ("r3_col",   "SCREEN2", "VDP(3)=&HFF",        3),
    ("r4_pat",   "SCREEN2", "VDP(4)=&H03",        4),
    ("r5_satr",  "SCREEN2", "VDP(5)=&H36",        5),
    ("r6_spat",  "SCREEN2", "VDP(6)=&H07",        6),
    ("val256",   "SCREEN0", "VDP(1)=256",         1),
    ("valneg",   "SCREEN0", "VDP(1)=-1",          1),
    ("valfrac",  "SCREEN0", "VDP(1)=2.7",         1),
    ("n8",       "SCREEN0", "VDP(8)=1",           8),
    ("nneg",     "SCREEN0", "VDP(-1)=1",          0),
    ("n9",       "SCREEN0", "VDP(9)=1",           0),
]


def c3_vdp_write():
    print("\n=== C3  VDP(n)= write (readback / shadow, or E<err>) ===")
    progs = []
    for lab, s, stmt, n in C3_CASES:
        rb = f"VDP({n})" if 0 <= n <= 8 else "0"
        sh = f"PEEK(&H{RG0SAV + (n if 0 <= n <= 7 else 0):04X})"
        progs.append(("stored", ["ON ERROR GOTO 40",
                                 f"{s}:{stmt}:A={rb}:B={sh}",
                                 'SCREEN0:PRINT"Q";A;"/";B:END',
                                 'SCREEN0:PRINT"E";ERR:END']))
    outs = omsx_repl.run_cases(REF, progs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for (lab, s, stmt, n), o in zip(C3_CASES, outs):
        hit = [" ".join(ln.split()) for ln in (o or "").splitlines()
               if ln.strip().startswith(("Q", "E"))]
        print(f"  {lab:9s} {s:8s} {stmt:20s} -> {hit[:1]}")


# ---- C4: BASE(n) read across modes ------------------------------------------
C4_CASES = [(f"s{m}_b{n}", f"SCREEN{m}", f"BASE({n})")
            for m in (0, 1, 2)
            for n in list(range(0, 21)) + [-1, 21, 22]]


def c4_base_read():
    print("\n=== C4  BASE(n) read per mode (value, or E<err>) ===")
    progs = [("stored", ["ON ERROR GOTO 40",
                         f"{s}:A={e}",
                         'SCREEN0:PRINT"Q";A:END',
                         'SCREEN0:PRINT"E";ERR:END'])
             for lab, s, e in C4_CASES]
    outs = omsx_repl.run_cases(REF, progs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for (lab, s, e), o in zip(C4_CASES, outs):
        hit = [" ".join(ln.split()) for ln in (o or "").splitlines()
               if ln.strip().startswith(("Q", "E"))]
        print(f"  {lab:10s} {e:12s} -> {hit[:1]}")


# ---- C5: BASE(n)= write -----------------------------------------------------
# Does the assignment stick in the BASE table, does it move the VDP register,
# and does a following CLS / mode set honour it?
C5_CASES = [
    ("b0_s0",    "SCREEN0", "BASE(0)=&H0400",  0, 2),
    ("b5_s1",    "SCREEN1", "BASE(5)=&H1C00",  5, 2),
    ("b10_s2",   "SCREEN2", "BASE(10)=&H1C00", 10, 2),
    ("b11_s2",   "SCREEN2", "BASE(11)=&H2400", 11, 3),
    ("b12_s2",   "SCREEN2", "BASE(12)=&H0000", 12, 4),
    ("b13_s2",   "SCREEN2", "BASE(13)=&H1F00", 13, 5),
    ("b14_s2",   "SCREEN2", "BASE(14)=&H3800", 14, 6),
    ("odd_val",  "SCREEN2", "BASE(10)=&H1801", 10, 2),
    ("big_val",  "SCREEN2", "BASE(10)=&H4000", 10, 2),
    ("neg_val",  "SCREEN2", "BASE(10)=-1",     10, 2),
    ("bad_n",    "SCREEN2", "BASE(21)=0",      10, 2),
    ("negn",     "SCREEN2", "BASE(-1)=0",      10, 2),
]


def c5_base_write():
    print("\n=== C5  BASE(n)= write (readback / VDP reg, or E<err>) ===")
    progs = []
    for lab, s, stmt, n, reg in C5_CASES:
        progs.append(("stored", ["ON ERROR GOTO 40",
                                 f"{s}:{stmt}:A=BASE({n}):B=VDP({reg})",
                                 'SCREEN0:PRINT"Q";A;"/";B:END',
                                 'SCREEN0:PRINT"E";ERR:END']))
    outs = omsx_repl.run_cases(REF, progs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for (lab, s, stmt, n, reg), o in zip(C5_CASES, outs):
        hit = [" ".join(ln.split()) for ln in (o or "").splitlines()
               if ln.strip().startswith(("Q", "E"))]
        print(f"  {lab:9s} {s:8s} {stmt:18s} -> {hit[:1]}")


def main() -> int:
    which = sys.argv[1:] or ["c1", "c2", "c3", "c4", "c5"]
    if "c1" in which: c1_tokens()
    if "c2" in which: c2_vdp_read()
    if "c3" in which: c3_vdp_write()
    if "c4" in which: c4_base_read()
    if "c5" in which: c5_base_write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
