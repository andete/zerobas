#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G8 `VDP(n)` / `BASE(n)=` characterization round 2 (Philips VG-8020).

Round 1 (g8_vdp_char1.py) pinned the tokens, the VDP(n) read map and the write
domains via SCREEN-0 text capture. That method DIES for `BASE(n)=` -- the
assignment moves the name-table base, so the screen scrape reads the wrong VRAM
and every case came back blank. Round 2 therefore reports through MEMORY
($D100..) with `capture=("mem_abs", ...)`, boot-per-case (a wrecked display does
not recover), and adds the two questions round 1 could not answer:

  D1 basewr  -- BASE(n)=v: value read back, the VDP register that shadows it
  D2 hwreach -- does VDP(n)= reach the CHIP or only the RAM shadow?  (clear R1's
                interrupt-enable bit and watch TIME: frozen => the chip saw it)
  D3 coerce  -- fractional index / value: truncate or round?
  D4 modeset -- does a later SCREEN honour a changed BASE, or overwrite it?
"""
from __future__ import annotations
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
RES = 0xD100          # result block: [0]=status 255 none/0 ok/1 err, [1..]=data
CAP = ("mem_abs", [(RES, 8)])


def prog(setup: str, stmt: str, report: str) -> tuple[str, list[str]]:
    """A stored program that reports through RES instead of the screen."""
    return ("stored", [
        "ON ERROR GOTO 60",
        f"POKE&H{RES:04X},255",
        f"{setup}:{stmt}",
        report,                                   # fills RES+1.. then RES=0
        "END",
        f"POKE&H{RES:04X},1:POKE&H{RES+1:04X},ERR:END",
    ])


def lo_hi(var: str, off: int) -> str:
    return (f"POKE&H{RES+off:04X},{var}-INT({var}/256)*256:"
            f"POKE&H{RES+off+1:04X},INT({var}/256)")


def decode(raw: str | None) -> str:
    if not raw:
        return "<no capture>"
    b = bytes.fromhex(raw)
    if b[0] == 255:
        return "<not reached>"
    if b[0] == 1:
        return f"ERR {b[1]}"
    return f"val={b[1] | (b[2] << 8):5d} reg={b[3]:3d}"


# ---- D1: BASE(n)= -----------------------------------------------------------
D1_CASES = [
    ("b0_s0",    "SCREEN0", "BASE(0)=&H0400",  0,  2),
    ("b5_s1",    "SCREEN1", "BASE(5)=&H1C00",  5,  2),
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
    ("crossmode", "SCREEN0", "BASE(10)=&H1C00", 10, 2),   # SCREEN-2 slot from S0
]


def d1_base_write():
    print("=== D1  BASE(n)= write (value read back / VDP reg) ===")
    progs = [prog(s, stmt, f"A=BASE({n}):B=VDP({reg}):{lo_hi('A', 1)}:"
                           f"POKE&H{RES+3:04X},B:POKE&H{RES:04X},0")
             for lab, s, stmt, n, reg in D1_CASES]
    outs = omsx_repl.run_cases(REF, progs, batch=False, capture=CAP, cart=None)
    for (lab, s, stmt, n, reg), o in zip(D1_CASES, outs):
        print(f"  {lab:10s} {s:8s} {stmt:18s} BASE({n})/VDP({reg}) -> {decode(o)}")


# ---- D2: does the write reach the chip? -------------------------------------
# Clearing R1 bit 5 (IE) stops the VBLANK interrupt -> TIME (JIFFY) freezes.
# A shadow-only write leaves TIME running.  Restore the bit before reporting.
D2_CASES = [
    ("ie_off",  "VDP(1)=VDP(1)AND223"),
    ("control", "A=0"),                      # baseline: TIME must advance
]


def d2_hw_reach():
    print("\n=== D2  does VDP(n)= reach the chip?  (TIME delta; 0 => yes) ===")
    progs = []
    for lab, stmt in D2_CASES:
        progs.append(("stored", [
            "ON ERROR GOTO 60",
            f"POKE&H{RES:04X},255",
            f"SCREEN0:{stmt}",
            "T=TIME:FOR I=1 TO 3000:NEXT:D=TIME-T",
            "VDP(1)=VDP(1)OR32",
            f"{lo_hi('D', 1)}:POKE&H{RES:04X},0:END",
            f"POKE&H{RES:04X},1:POKE&H{RES+1:04X},ERR:END",
        ]))
    outs = omsx_repl.run_cases(REF, progs, batch=False, capture=CAP, cart=None)
    for (lab, stmt), o in zip(D2_CASES, outs):
        print(f"  {lab:8s} {stmt:22s} -> {decode(o)}")


# ---- D3: fractional index / value -------------------------------------------
# In SCREEN 0 the shadows differ per register, so the chosen index is visible:
# VDP(0)=0, VDP(1)=240, VDP(2)=0, VDP(4)=1, VDP(7)=244.
D3_CASES = [
    ("idx_0_6",  "SCREEN0", "A=VDP(0.6)"),      # 0 => truncate, 1(=240) => round
    ("idx_1_5",  "SCREEN0", "A=VDP(1.5)"),
    ("idx_3_9",  "SCREEN0", "A=VDP(3.9)"),      # 3=>0, 4=>1
    ("idx_neg",  "SCREEN0", "A=VDP(-0.4)"),     # -0.4 -> 0 or ERR 5?
    ("val_2_5",  "SCREEN0", "VDP(0)=2.5:A=VDP(0)"),
    ("val_2_9",  "SCREEN0", "VDP(0)=2.9:A=VDP(0)"),
    ("val_m0_4", "SCREEN0", "VDP(0)=-0.4:A=VDP(0)"),
    ("val_255_6", "SCREEN0", "VDP(0)=255.6:A=VDP(0)"),
]


def d3_coerce():
    print("\n=== D3  fractional index / value coercion ===")
    progs = [prog(s, stmt, f"{lo_hi('A', 1)}:POKE&H{RES:04X},0")
             for lab, s, stmt in D3_CASES]
    outs = omsx_repl.run_cases(REF, progs, batch=False, capture=CAP, cart=None)
    for (lab, s, stmt), o in zip(D3_CASES, outs):
        d = decode(o)
        print(f"  {lab:10s} {stmt:26s} -> {d}")


# ---- D4: does a later SCREEN honour a changed BASE? -------------------------
D4_CASES = [
    ("s2_then_s2", "SCREEN2:BASE(10)=&H1C00:SCREEN2", 10, 2),
    ("s2_then_s0", "SCREEN2:BASE(10)=&H1C00:SCREEN0", 10, 2),
    ("s0_base_s2", "SCREEN0:BASE(10)=&H1C00:SCREEN2", 10, 2),
    ("s0_base_cls", "SCREEN0:BASE(0)=&H0400:CLS",      0, 2),
]


def d4_modeset():
    print("\n=== D4  BASE vs a later SCREEN / CLS ===")
    progs = [prog("A=0", seq, f"A=BASE({n}):B=VDP({reg}):{lo_hi('A', 1)}:"
                              f"POKE&H{RES+3:04X},B:POKE&H{RES:04X},0")
             for lab, seq, n, reg in D4_CASES]
    outs = omsx_repl.run_cases(REF, progs, batch=False, capture=CAP, cart=None)
    for (lab, seq, n, reg), o in zip(D4_CASES, outs):
        print(f"  {lab:12s} {seq:34s} -> {decode(o)}")


def main() -> int:
    which = sys.argv[1:] or ["d1", "d2", "d3", "d4"]
    if "d1" in which: d1_base_write()
    if "d2" in which: d2_hw_reach()
    if "d3" in which: d3_coerce()
    if "d4" in which: d4_modeset()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
