#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-XSLOTPRICE phase 0b -- the price of ONE inter-slot call, disk.rom -> main page 1.

SIX CASES, ONE BUILD, ONE POKE APART. Every case runs the SAME 100 hook entries
through the SAME ROM; only $E771 -- the number of inter-slot calls the disk-ROM
handler makes per entry -- differs, and BASIC POKEs it. So the slope of frames
against calls cannot be a different machine, a different build, or a different
boot.

⚠️ EVERY CASE IS KEPT UNDER ~120 FRAMES ON PURPOSE. Longer programs come back
with an empty capture, and that boundary is the HARNESS: a plain `FOR I=1 TO
2000:NEXT` that touches no hook at all goes equally quiet (scratchpad/
p0b_window2.py). A silent case is therefore not a reading about inter-slot
calls, and none is reported as one.

🎯 THE WITNESS IS TWO-SIDED, and it is printed for every armed case. The callee
returns the byte at $4002: 16 in the main ROM, 52 in the disk ROM. 16 proves
main page 1 was mapped while our callee ran; 52 would prove the switch never
happened and we had merely called into ourselves.
"""
from __future__ import annotations
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
ITERS = 100
ARMS = [0, 1, 8, 16, 32, 64]


def case(n):
    return (f"n{n:02d}", [
        f"10 POKE &HE771,{n}:T=TIME",
        f'20 FOR I=1 TO {ITERS}:X=CVI("AB"):NEXT',
        '30 PRINT "[";PEEK(&HE770);TIME-T;"]"',
        "RUN",
    ])


def main() -> int:
    cases = [case(n) for n in ARMS]
    caps = omsx_repl.run_cases(ZB, cases, batch=False, reset=(), boot=8.0,
                               step=3.0, cap_gap=45.0, timeout=1800.0)
    read = {}
    for n, cap in zip(ARMS, caps):
        m = re.search(r"\[\s*(-?\d+)\s+(-?\d+)\s*\]", cap or "")
        read[n] = (int(m.group(1)), int(m.group(2))) if m else None
        w, f = read[n] if read[n] else ("-", "-")
        print(f"  N={n:<3d} witness={w:>5}  {f:>5} frames / {ITERS} hook entries")

    if read.get(0) is None:
        print("\nINSTRUMENT FAULT (rc 2): no N=0 baseline -- nothing to subtract.")
        return 2
    base = read[0][1]
    bad = [n for n in ARMS if n and read[n] and read[n][0] != 0x10]
    if bad:
        print(f"\n🔴 witness is not main's byte for N={bad} -- the call did not "
              f"reach main page 1. No price is reported.")
        return 1

    print(f"\nbaseline N=0 (hook entered, no inter-slot call): {base} frames")
    pts = []
    for n in ARMS:
        if not n or read[n] is None:
            continue
        calls = n * ITERS
        d = read[n][1] - base
        pts.append((calls, d))
        print(f"  {calls:6d} calls  +{d:4d} frames  "
              f"= {d / calls:.5f} frames/call = {d * 1000.0 / 60.0 / calls:.4f} ms/call")
    if len(pts) < 2:
        print("\nfewer than two armed readings survived -- a slope needs two.")
        return 2
    # least squares through the origin: the model is "cost is per call"
    slope = sum(x * y for x, y in pts) / sum(x * x for x, _ in pts)
    print(f"\nfit through the origin over {len(pts)} point(s): "
          f"{slope:.5f} frames/call = {slope * 1000.0 / 60.0:.4f} ms/call "
          f"= {1.0 / slope:.0f} inter-slot calls per frame")
    return 0


if __name__ == "__main__":
    sys.exit(main())
