#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G8 characterization round 7 (Philips VG-8020): decide the SCREEN-1/2 quirk.

Round 4 established that `BASE(n)=` in SCREEN 0 or SCREEN 3 updates exactly the
one VDP register the slot owns, while in SCREEN 1 or SCREEN 2 it instead leaves
the chip programmed the way the NEXT group's table describes.  Every case so far
is ambiguous about the source of those register values, because the next group's
defaults happen to agree with the current group's for the untouched registers.

Round 7 breaks the tie by POISONING the next group's table first (from SCREEN 0,
where round 4 proved a write only stores the word), then entering the mode and
writing a slot.  If the poisoned value shows up in the register, the reprogram
genuinely reads the NEXT group's entries.
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


def decode(raw):
    if not raw:
        return None
    b = bytes.fromhex(raw)
    if b[50] != 7:
        return None
    return ([b[2 * i] | (b[2 * i + 1] << 8) for i in range(20)], list(b[40:49]), b[49])


def prog(lines):
    body = list(lines) + [f"POKE&H{RES:04X},7"]
    return ("stored", body + [f"GOTO {(len(body) + 1) * 10}"])


def regs(o) -> str:
    d = decode(o)
    return "<none>" if d is None else " ".join(f"R{i}={v:#04x}" for i, v in
                                               enumerate(d[1][:8]))


CASES = [
    # (label, lines)  -- poison, enter the mode, write a slot, hold
    ("s1_poison_satr",
     ["SCREEN0", "BASE(13)=&H0400", "SCREEN1", "BASE(8)=&H1F00"]),
    ("s1_poison_name",
     ["SCREEN0", "BASE(10)=&H2400", "SCREEN1", "BASE(5)=&H0400"]),
    ("s1_clean",
     ["SCREEN1", "BASE(8)=&H1F00"]),
    ("s2_poison_satr",
     ["SCREEN0", "BASE(18)=&H0400", "SCREEN2", "BASE(13)=&H1F00"]),
    ("s2_poison_spat",
     ["SCREEN0", "BASE(19)=&H1000", "SCREEN2", "BASE(14)=&H3000"]),
    ("s2_clean",
     ["SCREEN2", "BASE(13)=&H1F00"]),
    # does a plain SCREEN re-entry undo it?
    ("s2_then_screen",
     ["SCREEN2", "BASE(13)=&H1F00", "SCREEN2"]),
    # baselines for reference
    ("base_s1", ["SCREEN1"]),
    ("base_s2", ["SCREEN2"]),
]


def main() -> int:
    print("=== I1  where do the reprogrammed registers come from? ===")
    outs = omsx_repl.run_cases(REF, [prog(l) for _, l in CASES], batch=False,
                               capture=CAP, step=6.0, cart=None)
    for (lab, lines), o in zip(CASES, outs):
        print(f"  {lab:16s} {':'.join(lines):46s}")
        print(f"        -> {regs(o)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
