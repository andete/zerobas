#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-XSLOTPRICE phase 0c -- what actually happens to interrupts inside a
disk-ROM hook handler, and whether htimi_guard is even the mechanism.

🔴 THE QUESTION CHANGED UNDER MEASUREMENT. 0c was filed as "confirm htimi_guard
covers the disk-ROM window". Measuring it found something upstream: a hook
handler is entered through the inter-slot CALLF, which leaves INTERRUPTS OFF, so
during the disk-ROM window nothing runs at all -- not H.TIMI, not the guard, and
not the BIOS timer ISR that drives TIME. The guard cannot "cover" a window in
which it is never reached.

THE TWO-SIDED CONTROL. $E773 makes the disk-ROM spin run EI instead, page 0
being main throughout so $0038 is live. Same spin, same ROM, one bit apart:

  ei=0  interrupts as the hook handler receives them
        -> TIME must barely move: the timer ISR is not running
  ei=1  interrupts on while the DISK ROM owns page 1
        -> TIME must advance normally (the BIOS ISR is page-0 and runs), while
           INTERVAL must NOT tick (htimi_guard sees a nonzero page-1 primary
           field and skips event_poll). That combination is the guard doing
           exactly its job, and it is separable from "nothing ran".

Reading both numbers is the point: TIME alone cannot tell "the guard skipped"
from "no interrupt happened", and fires alone cannot either.
"""
from __future__ import annotations
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
SPIN = 2          # 2 x 65536 idle iterations ~ 1 s of real work in the disk ROM
CB = 3200         # inter-slot call-backs costing ~ the same ~1 s, in MAIN page 1


def case(name, cb, spin, ei):
    return (name, [
        f"10 POKE &HE772,{spin}:POKE &HE773,{ei}",
        f"20 POKE &HE771,{cb % 256}:C=0",
        "30 ON INTERVAL=1 GOSUB 100",
        f'40 INTERVAL ON:T=TIME:FOR J=1 TO {max(1, cb // 256)}',
        '50 X=CVI("AB"):NEXT',
        "60 F=TIME-T:INTERVAL OFF",
        '70 PRINT "[";C;F;"]"',
        "80 END",
        "100 C=C+1:RETURN",
        "RUN",
    ])


ARMS = [
    ("disk.ei0", 0, SPIN, 0),   # as a handler is entered today: interrupts OFF
    ("disk.ei1", 0, SPIN, 1),   # interrupts ON, page 1 = DISK ROM -> guard skips
    ("cb.ei1", CB, 0, 1),       # interrupts ON, page 1 = MAIN -> guard must pass
    ("base", 0, 0, 1),          # no spin, no call-back: the instrument's own rate
]


def main() -> int:
    cases = [case(n, cb, sp, ei) for n, cb, sp, ei in ARMS]
    for n, lines in cases:
        for ln in lines:
            if len(ln) > 38:
                print(f"INSTRUMENT FAULT: {n}: {len(ln)} cols: {ln!r}")
                return 2
    caps = omsx_repl.run_cases(ZB, cases, batch=False, reset=(), boot=8.0,
                               step=3.0, cap_gap=60.0, timeout=1800.0)
    got = {}
    print(f"{'arm':10s} {'fires':>6s} {'frames':>7s} {'ticked':>8s}")
    for (n, _), cap in zip(cases, caps):
        m = re.search(r"\[\s*(-?\d+)\s+(-?\d+)\s*\]", cap or "")
        if not m:
            print(f"{n:10s} {'<NO FENCE>':>6s}")
            continue
        c, f = int(m.group(1)), int(m.group(2))
        got[n] = (c, f)
        print(f"{n:10s} {c:6d} {f:7d} {c / f * 100:7.1f}%" if f else
              f"{n:10s} {c:6d} {f:7d}     n/a")
    print()
    print("disk.ei0: TIME itself barely moves -- interrupts are OFF, so the BIOS")
    print("          timer ISR is not running either. htimi_guard never gets a turn.")
    print("disk.ei1: TIME advances normally but INTERVAL does not tick -- the guard")
    print("          IS covering the disk-ROM window, and that is it doing its job.")
    print("cb.ei1  : page 1 is MAIN during the call-back, so the guard must PASS and")
    print("          INTERVAL must tick at close to the baseline rate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
