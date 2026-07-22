#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G8 characterization round 8 (Philips VG-8020): how WIDE is the reprogram?

Implementation question left open by rounds 4/7.  In SCREEN 0 and SCREEN 3 a
`BASE(n)=` write appeared to move exactly one register -- but every other
register it might have rewritten already held the value the table implies, so
"one register" and "all seven, from the table" are indistinguishable there.

Round 8 breaks that symmetry with `VDP(n)=`: desync a register from its table
word first, then write a DIFFERENT slot.  If the desynced register snaps back to
the table's value, the handler reprograms the whole set; if it keeps the poked
value, only the written slot's register moves.  The same probe also measures how
many registers the SCREEN-1/2 off-by-one path writes.
"""
from __future__ import annotations
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
BASETAB, RGSAV, SCRMOD, RES = 0xF3B3, 0xF3DF, 0xFCAF, 0xD100
CAP = ("mem_abs", [(BASETAB, 40), (RGSAV, 9), (SCRMOD, 1), (RES, 1)])


def prog(lines):
    body = list(lines) + [f"POKE&H{RES:04X},7"]
    return ("stored", body + [f"GOTO {(len(body) + 1) * 10}"])


def regs(o) -> str:
    if not o:
        return "<none>"
    b = bytes.fromhex(o)
    if b[50] != 7:
        return "<not reached>"
    return " ".join(f"R{i}={v:#04x}" for i, v in enumerate(b[40:47]))


CASES = [
    # SCREEN 0: desync R2 (name) and R6 (sprite pattern), then write the satr slot
    ("s0_desync", ["SCREEN0", "VDP(2)=5", "VDP(6)=5", "BASE(3)=&H1F00"]),
    ("s0_ctl",    ["SCREEN0", "VDP(2)=5", "VDP(6)=5"]),
    # SCREEN 1: same desync, then a group-1 write (the off-by-one path)
    ("s1_desync", ["SCREEN1", "VDP(2)=5", "VDP(6)=5", "BASE(8)=&H1F00"]),
    ("s1_ctl",    ["SCREEN1", "VDP(2)=5", "VDP(6)=5"]),
    # SCREEN 2: ditto
    ("s2_desync", ["SCREEN2", "VDP(2)=5", "VDP(6)=5", "BASE(13)=&H1F00"]),
    ("s2_ctl",    ["SCREEN2", "VDP(2)=5", "VDP(6)=5"]),
    # SCREEN 0, cross-group write: must touch nothing at all
    ("s0_cross",  ["SCREEN0", "VDP(2)=5", "VDP(6)=5", "BASE(13)=&H1F00"]),
]


def main() -> int:
    print("=== J1  reprogram width (poke a register out of sync, then write) ===")
    outs = omsx_repl.run_cases(REF, [prog(l) for _, l in CASES], batch=False,
                               capture=CAP, step=6.0, cart=None)
    for (lab, lines), o in zip(CASES, outs):
        print(f"  {lab:10s} {':'.join(lines):48s}")
        print(f"        -> {regs(o)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
