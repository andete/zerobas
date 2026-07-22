#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G8 characterization round 5 (Philips VG-8020): the BASE(n)= value domain.

Rounds 1-4 pinned WHAT `BASE(n)=` does; round 5 pins WHICH VALUES it accepts.
Two things make this cheap to batch even though a successful write can wreck the
display: the result is reported through MEMORY (so a scrambled name table does
not blind the capture), and every case RESTORES the slot's default and returns
to SCREEN 0 before the next one is injected.

Reports per case: OK (accepted) / E<n> (error code), plus the value read back.
"""
from __future__ import annotations
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
RES = 0xD100
CAP = ("mem_abs", [(RES, 4)])

# power-on defaults, from the round-3/4 baseline dump
DEFAULT = [0x0000, 0x0000, 0x0800, 0x0000, 0x0000,
           0x1800, 0x2000, 0x0000, 0x1B00, 0x3800,
           0x1800, 0x2000, 0x0000, 0x1B00, 0x3800,
           0x0800, 0x0000, 0x0000, 0x1B00, 0x3800]
SLOTNAME = ["name", "colr", "patt", "satr", "spat"]

VALUES = [0x0000, 0x0080, 0x0100, 0x0400, 0x0401, 0x0800, 0x0C00, 0x1000,
          0x1800, 0x1801, 0x1C00, 0x2000, 0x2400, 0x3800, 0x3F80, 0x3FFF,
          0x4000, 0x8000]


def case(mode: int, n: int, v: int):
    return ("stored", [
        "ON ERROR GOTO 70",
        f"POKE&H{RES:04X},255",
        f"SCREEN{mode}",
        f"BASE({n})=&H{v:04X}",
        f"A=BASE({n}):POKE&H{RES+1:04X},A-INT(A/256)*256:"
        f"POKE&H{RES+2:04X},INT(A/256):POKE&H{RES:04X},0",
        f"BASE({n})=&H{DEFAULT[n]:04X}:SCREEN0:END",
        f"POKE&H{RES:04X},1:POKE&H{RES+1:04X},ERR:SCREEN0:END",
    ])


def decode(raw: str | None) -> str:
    if not raw:
        return "<no capture>"
    b = bytes.fromhex(raw)
    if b[0] == 255:
        return "<not reached>"
    if b[0] == 1:
        return f"E{b[1]}"
    return f"OK({b[1] | (b[2] << 8):#06x})"


def cross() -> None:
    """Is the value check tied to the SLOT's group or to the CURRENT mode?

    Every accepted/rejected value so far was measured with the current mode
    equal to the slot's own group.  Here the two are deliberately split: the
    group-2 and group-3 slots are written from SCREEN 0, where (per round 4) no
    VDP reprogramming happens at all -- so any error can only come from a
    slot-group-driven check.  Group 3 (SCREEN 3 / multicolor) can ONLY be probed
    this way on our side, since zerobas has no SCREEN 3.
    """
    print("=== G2  value check from a foreign mode (written from SCREEN 0) ===")
    cases, labels = [], []
    for n in list(range(10, 20)):
        for v in VALUES:
            cases.append(case(0, n, v))
            labels.append((n, n % 5, v))
    outs = omsx_repl.run_cases(REF, cases, batch=True, reset=("NEW",),
                               capture=CAP, cart=None)
    acc: dict[tuple[int, int], list[str]] = {}
    for (n, k, v), o in zip(labels, outs):
        d = decode(o)
        acc.setdefault((n, k), []).append(f"{v:#06x}" if d.startswith("OK") else "")
    for (n, k), oks in acc.items():
        print(f"  BASE({n:2d},{SLOTNAME[k]}) OK={' '.join(x for x in oks if x)}")


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] == "cross":
        cross()
        return 0
    modes = [int(x) for x in (argv or ["0", "1", "2"])]
    for m in modes:
        print(f"=== G1  BASE(n)=v accepted values, SCREEN {m} ===")
        cases, labels = [], []
        for k in range(5):
            n = m * 5 + k
            for v in VALUES:
                cases.append(case(m, n, v))
                labels.append((n, k, v))
        outs = omsx_repl.run_cases(REF, cases, batch=True, reset=("NEW",),
                                   capture=CAP, cart=None)
        for (n, k, v), o in zip(labels, outs):
            print(f"  BASE({n:2d},{SLOTNAME[k]}) = {v:#06x} -> {decode(o)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
