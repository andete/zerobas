#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G8 characterization round 4 (Philips VG-8020): the BASE(n)= reprogram rule.

Round 3 showed `BASE(n)=` does two things -- store the word, and (sometimes)
reprogram the VDP -- but the reprogram looked WRONG: in SCREEN 1 a group-1 write
left the chip holding SCREEN-2 register values, and in SCREEN 2 a group-2 write
left it holding SCREEN-3 (multicolor) values, while in SCREEN 0 a group-0 write
moved exactly one register.  Two hypotheses fit:

  H-A  the handler reprograms from the NEXT group's table entries (off-by-one)
  H-B  the handler also MOVES THE SCREEN MODE to group+1 and then does an
       ordinary mode setup for that new mode

They are told apart by SCRMOD ($FCAF), which round 3 did not capture.  Round 4
grids every slot against its own group's mode with SCRMOD in the dump.
"""
from __future__ import annotations
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
BASETAB = 0xF3B3
RGSAV = 0xF3DF
SCRMOD = 0xFCAF           # current screen mode
RES = 0xD100
CAP = ("mem_abs", [(BASETAB, 40), (RGSAV, 9), (SCRMOD, 1), (RES, 1)])

SLOTNAME = ["name", "colr", "patt", "satr", "spat"]
# a distinct, legal-looking value per slot kind (aligned to that table's grain)
TESTVAL = {0: "&H0400", 1: "&H2000", 2: "&H0800", 3: "&H1F00", 4: "&H3000"}


def decode(raw: str | None):
    if not raw:
        return None
    b = bytes.fromhex(raw)
    if b[50] != 7:
        return None
    return ([b[2 * i] | (b[2 * i + 1] << 8) for i in range(20)],
            list(b[40:49]), b[49])


def show_diff(before, after) -> str:
    if before is None or after is None:
        return "<no capture / error>"
    bb, br, bm = before
    ab, ar, am = after
    parts = []
    for i, (x, y) in enumerate(zip(bb, ab)):
        if x != y:
            parts.append(f"BASE({i}) {x:#06x}->{y:#06x}")
    for i, (x, y) in enumerate(zip(br, ar)):
        if x != y:
            parts.append((f"R{i}" if i < 8 else "STATFL") + f" {x:#04x}->{y:#04x}")
    if bm != am:
        parts.append(f"SCRMOD {bm}->{am}")
    return ", ".join(parts) if parts else "(no change)"


def prog(lines: list[str]) -> tuple[str, list[str]]:
    body = list(lines) + [f"POKE&H{RES:04X},7"]
    hold = (len(body) + 1) * 10
    return ("stored", body + [f"GOTO {hold}"])


CASES = []
for g in range(4):                       # group 0..3  <-> SCREEN 0..3
    for k in range(5):
        n = g * 5 + k
        CASES.append((f"m{g}_b{n}_{SLOTNAME[k]}", f"SCREEN{g}",
                      f"BASE({n})={TESTVAL[k]}"))
# cross-mode controls: write a group's slot from a different mode
CASES += [
    ("m0_b10", "SCREEN0", "BASE(10)=&H1C00"),
    ("m2_b5",  "SCREEN2", "BASE(5)=&H1C00"),
    ("m2_b15", "SCREEN2", "BASE(15)=&H0C00"),
]


def main() -> int:
    print("=== F1  BASE(n)= reprogram rule (BASE table + regs + SCRMOD) ===")
    progs = []
    for lab, mode, stmt in CASES:
        progs.append(prog([mode]))
        progs.append(prog([mode, stmt]))
    outs = omsx_repl.run_cases(REF, progs, batch=False, capture=CAP,
                               step=6.0, cart=None)
    for i, (lab, mode, stmt) in enumerate(CASES):
        print(f"  {lab:16s} {mode:8s} {stmt:20s} -> "
              f"{show_diff(decode(outs[2 * i]), decode(outs[2 * i + 1]))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
