#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-XSLOTPRICE 0b -- the COMPARATIVE frame Joost fixed for the kill criterion.

0.156 ms per inter-slot call is a number with no meaning on its own. The
criterion is comparative: does OUR call cost roughly what the architecture
inherently costs, or dramatically more? So price it against the work that
surrounds it, on the same machine, in the same loop shape, 100 iterations each:

  empty   FOR/NEXT only ................ the loop's own tax
  assign  X=1 ......................... the interpreter's per-statement floor
  cvi     X=CVI("AB") with N=0 ........ + one HOOK entry (main -> disk, RST 30h)
                                         and the whole CVI argument evaluation

The hook entry is itself an inter-slot call, and it is one the REFERENCE pays
too on every disk verb -- so `cvi minus assign` is the architecture's own
overhead measured on our machine, and the call-back has to be read against it.
"""
from __future__ import annotations
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
ITERS = 100
BODIES = [("empty", "I=I"), ("assign", "X=1"), ("cvi", 'X=CVI("AB")')]


def main() -> int:
    cases = [(n, ["10 POKE &HE771,0:T=TIME",
                  f"20 FOR I=1 TO {ITERS}:{b}:NEXT",
                  '30 PRINT "[";TIME-T;"]"', "RUN"]) for n, b in BODIES]
    caps = omsx_repl.run_cases(ZB, cases, batch=False, reset=(), boot=8.0,
                               step=3.0, cap_gap=45.0, timeout=1200.0)
    got = {}
    for (n, _), cap in zip(cases, caps):
        m = re.search(r"\[\s*(-?\d+)\s*\]", cap or "")
        got[n] = int(m.group(1)) if m else None
        print(f"  {n:8s} {got[n] if got[n] is not None else '<NO FENCE>'} frames "
              f"/ {ITERS} iterations")
    if any(v is None for v in got.values()):
        print("\nINSTRUMENT FAULT (rc 2): a case went quiet; no comparison.")
        return 2
    ms = {k: v * 1000.0 / 60.0 / ITERS for k, v in got.items()}
    print(f"\n  per iteration: empty {ms['empty']:.3f} ms, "
          f"assign {ms['assign']:.3f} ms, cvi {ms['cvi']:.3f} ms")
    print(f"  one HOOK entry + CVI evaluation  = {ms['cvi'] - ms['assign']:.3f} ms")
    print(f"  one CALL-BACK (measured, 5-point) = 0.156 ms")
    denom = ms['cvi'] - ms['assign']
    if denom > 0:
        print(f"\n  a call-back is {0.156 / denom * 100:.0f}% of the hook entry "
              f"the verb already pays to get here,")
    print(f"  and {0.156 / ms['cvi'] * 100:.0f}% of one interpreted CVI statement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
